"""
Router: /templates
Gerencia templates de tarefas com palavras-chave para vinculação automática de PDFs.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import uuid, tempfile, os

from app.models.enums import Department
from app.models.task_template import TaskTemplate
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService

router   = APIRouter()
repo:     MockRepository = None
pdf_svc:  PDFService     = None


# ── SCHEMAS ───────────────────────────────────────────────────────────

class TemplateCreateRequest(BaseModel):
    name:       str
    department: Department
    keywords:   list[str]
    created_by: str


class TemplateMatchRequest(BaseModel):
    raw_text: str   # texto extraído do PDF para testar contra os templates


# ── CRUD ──────────────────────────────────────────────────────────────

@router.get("/", summary="Listar templates")
def list_templates():
    return [t.summary() for t in repo.list_templates()]


@router.get("/{template_id}", summary="Buscar template por ID")
def get_template(template_id: str):
    t = repo.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    return t.summary()


@router.post("/", summary="Criar template de tarefa")
def create_template(body: TemplateCreateRequest):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nome obrigatório.")
    if not body.keywords:
        raise HTTPException(status_code=400, detail="Informe ao menos uma palavra-chave.")
    t = TaskTemplate(
        id=str(uuid.uuid4())[:8],
        name=body.name.strip(),
        department=body.department,
        keywords=[k.strip() for k in body.keywords if k.strip()],
        created_by=body.created_by,
    )
    repo.save_template(t)
    return t.summary()


@router.delete("/{template_id}", summary="Remover template")
def delete_template(template_id: str):
    deleted = repo.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    return {"deleted": True, "template_id": template_id}


# ── VALIDAÇÃO COM PDF MODELO ──────────────────────────────────────────

@router.post("/{template_id}/validate", summary="Validar template com PDF modelo")
async def validate_with_pdf(template_id: str, file: UploadFile = File(...)):
    """
    Recebe um PDF modelo e verifica se todas as palavras-chave do template
    estão presentes no conteúdo do arquivo.
    """
    t = repo.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas PDFs são aceitos.")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents); tmp_path = tmp.name

    try:
        extracao = pdf_svc.extract_from_file(tmp_path)
        matched, encontradas, faltando = t.matches(extracao.raw_text)
        return {
            "template_id":  template_id,
            "template_name": t.name,
            "valid":        matched,
            "found":        encontradas,
            "missing":      faltando,
            "confidence":   f"{len(encontradas)}/{len(t.keywords)}",
        }
    finally:
        os.unlink(tmp_path)


# ── MATCH DE PDF ──────────────────────────────────────────────────────

@router.post("/match/pdf", summary="Identificar qual template bate com um PDF")
async def match_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF e retorna qual template (se algum) reconhece o documento.
    Também retorna dados extraídos: tipo, competência, CNPJ, IE e empresa.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas PDFs são aceitos.")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents); tmp_path = tmp.name

    try:
        clientes = repo.list_clients()
        extracao = pdf_svc.extract_from_file(tmp_path, clients=clientes)
        template = repo.match_template(extracao.raw_text)

        client_info = None
        if extracao.client_match and extracao.client_match.client:
            c = extracao.client_match.client
            client_info = {
                "id":           c.id,
                "codigo":       c.codigo,
                "company_name": c.company_name,
                "matched_by":   extracao.client_match.matched_by,
                "matched_value":extracao.client_match.matched_value,
            }

        bloqueios = []
        if not template:
            bloqueios.append("Nenhuma tarefa cadastrada reconheceu este PDF")
        elif not client_info:
            bloqueios.append("Empresa não identificada — necessário selecionar manualmente")
        else:
            dept = template.department.value
            c = extracao.client_match.client
            emails = c.get_emails_for_department(dept)
            if not c.emails:
                bloqueios.append("Empresa sem nenhum e-mail cadastrado")
            elif not emails:
                todos = [ce.email for ce in c.emails]
                bloqueios.append(f"Nenhum e-mail configurado para {dept} — existentes: {', '.join(todos)}")

        return {
            "filename":             file.filename,
            "confidence":           round(extracao.confidence, 2),
            "extracted": {
                "competence":       extracao.suggested_competence,
                "cnpj":             extracao.suggested_company_cnpj,
                "ie":               extracao.suggested_company_ie,
            },
            "client":               client_info,
            "template":             template.summary() if template else None,
            "can_send":             len(bloqueios) == 0,
            "block_reasons":        bloqueios,
            "warnings":             extracao.warnings,
        }
    finally:
        os.unlink(tmp_path)

"""
Router: /clients
Gerencia empresas — importação via planilha e e-mails por departamento.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import tempfile, os

from app.repositories.mock_repository import MockRepository
from app.services.xlsx_service import XlsxService

router   = APIRouter()
repo:     MockRepository = None
xlsx_svc: XlsxService   = None


# ── SCHEMAS ───────────────────────────────────────────────────────────

class ClientEmailRequest(BaseModel):
    email:       str
    label:       str
    departments: list[str]


# ── LISTAR / BUSCAR ───────────────────────────────────────────────────

@router.get("/", summary="Listar todas as empresas")
def list_clients(q: Optional[str] = None):
    """
    Lista empresas. Parâmetro `q` filtra por nome, CNPJ, código ou IE.
    """
    clients = repo.list_clients(active_only=False)
    if q:
        ql = q.lower()
        clients = [c for c in clients if
                   ql in (c.company_name or "").lower() or
                   ql in (c.cnpj_digits() or "") or
                   ql in (c.codigo or "").lower() or
                   ql in (c.ie_digits() or "")]
    return [_client_json(c) for c in clients]


@router.get("/{client_id}", summary="Buscar empresa por ID")
def get_client(client_id: str):
    c = repo.get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return _client_json(c)


# ── IMPORTAÇÃO VIA PLANILHA ───────────────────────────────────────────

@router.post("/sync", summary="Importar/sincronizar empresas via planilha .xlsx")
async def sync_clients(file: UploadFile = File(...)):
    """
    Recebe um arquivo .xlsx com colunas NOME, CODIGO, CNPJ, IE.
    Aplica INSERT / UPDATE / DELETE comparando pelo CNPJ.
    E-mails já cadastrados são preservados no UPDATE.
    """
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx são aceitos.")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Preserva e-mails antes do sync
        emails_backup = {c.cnpj_digits(): c.emails for c in repo.list_clients(active_only=False)}
        result = xlsx_svc.sync(tmp_path, repo)

        # Restaura e-mails preservados
        for c in repo.list_clients(active_only=False):
            if c.cnpj_digits() in emails_backup:
                c.emails = emails_backup[c.cnpj_digits()]
                repo.save_client(c)

        return {
            "inserted": len(result.inserted),
            "updated":  len(result.updated),
            "deleted":  len(result.deleted),
            "errors":   result.errors,
            "total_active": len(repo.list_clients()),
        }
    finally:
        os.unlink(tmp_path)


# ── E-MAILS POR DEPARTAMENTO ──────────────────────────────────────────

@router.get("/{client_id}/emails", summary="Listar e-mails de uma empresa")
def list_emails(client_id: str):
    c = repo.get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return [{"email": ce.email, "label": ce.label, "departments": ce.departments} for ce in c.emails]


@router.post("/{client_id}/emails", summary="Adicionar e-mail a uma empresa")
def add_email(client_id: str, body: ClientEmailRequest):
    c = repo.get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    if "@" not in body.email:
        raise HTTPException(status_code=400, detail="E-mail inválido.")
    if any(ce.email == body.email.lower() for ce in c.emails):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado para esta empresa.")
    if not body.departments:
        raise HTTPException(status_code=400, detail="Informe ao menos um departamento.")
    ce = c.add_email(body.email, body.label, body.departments)
    repo.save_client(c)
    return {"email": ce.email, "label": ce.label, "departments": ce.departments}


@router.delete("/{client_id}/emails/{email}", summary="Remover e-mail de uma empresa")
def remove_email(client_id: str, email: str):
    c = repo.get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    removed = c.remove_email(email)
    if not removed:
        raise HTTPException(status_code=404, detail="E-mail não encontrado.")
    repo.save_client(c)
    return {"removed": True, "email": email}


@router.get("/{client_id}/emails/department/{department}", summary="E-mails de uma empresa para um departamento específico")
def emails_by_department(client_id: str, department: str):
    c = repo.get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    emails = c.get_emails_for_department(department)
    return {"department": department, "emails": emails, "count": len(emails)}


# ── HELPER ────────────────────────────────────────────────────────────

def _client_json(c) -> dict:
    tipo = "CPF" if len(c.cnpj_digits()) == 11 else "CNPJ"
    return {
        "id":                  c.id,
        "codigo":              c.codigo,
        "company_name":        c.company_name,
        "cnpj":                c.mask_cnpj(),
        "cnpj_raw":            c.cnpj_digits(),
        "tipo":                tipo,
        "inscricao_estadual":  c.inscricao_estadual,
        "emails":              [{"email": ce.email, "label": ce.label, "departments": ce.departments} for ce in c.emails],
        "responsible":         c.responsible,
        "department":          c.department,
        "active":              c.active,
    }

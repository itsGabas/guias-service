from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import tempfile, os

from app.models.enums import DocumentType, Department
from app.services.task_service import TaskService
from app.repositories.mock_repository import MockRepository

router   = APIRouter()
task_svc: TaskService      = None   # injetado pelo main.py
repo:     MockRepository   = None


# ── SCHEMAS (request/response) ────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    title:       str
    client_id:   str
    competence:  str
    department:  Department
    created_by:  str
    notes:       Optional[str] = None

class ConfirmDocumentRequest(BaseModel):
    doc_id: str


# ── ENDPOINTS ─────────────────────────────────────────────────────────

@router.post("/", summary="Criar nova tarefa")
def create_task(body: TaskCreateRequest):
    try:
        task = task_svc.create_task(
            title=body.title,
            client_id=body.client_id,
            competence=body.competence,
            department=body.department,
            created_by=body.created_by,
            notes=body.notes,
        )
        return task.summary()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", summary="Listar tarefas")
def list_tasks(
    client_id:  Optional[str] = None,
    status:     Optional[str] = None,
    department: Optional[str] = None,
):
    tasks = task_svc.list_tasks(
        client_id=client_id,
        status=status,
        department=department,
    )
    return [t.summary() for t in tasks]


@router.get("/{task_id}", summary="Buscar tarefa por ID")
def get_task(task_id: str):
    try:
        return task_svc.get_task(task_id).summary()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{task_id}", summary="Deletar tarefa")
def delete_task(task_id: str):
    deleted = repo.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"deleted": True, "task_id": task_id}


# ── DOCUMENTOS ────────────────────────────────────────────────────────

@router.post("/{task_id}/documents", summary="Upload de PDF e detecção automática")
async def upload_document(
    task_id:           str,
    file:              UploadFile = File(...),
    manual_type:       Optional[str] = Form(None),
    manual_competence: Optional[str] = Form(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    # Salva temporariamente para leitura pelo PyMuPDF
    contents = await file.read()
    size_kb  = len(contents) / 1024

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        doc_type = DocumentType(manual_type) if manual_type else None
        doc = task_svc.add_document_from_text(
            task_id=task_id,
            filename=file.filename,
            file_size_kb=size_kb,
            raw_text=_extract_text(tmp_path),
            file_path=tmp_path,
            manual_type=doc_type,
            manual_competence=manual_competence,
        )
        return doc.summary()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)


@router.post("/{task_id}/documents/confirm", summary="Confirmar documento após revisão")
def confirm_document(task_id: str, body: ConfirmDocumentRequest):
    try:
        doc = task_svc.confirm_document(task_id, body.doc_id)
        return doc.summary()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}/documents/{doc_id}", summary="Remover documento da tarefa")
def remove_document(task_id: str, doc_id: str):
    removed = task_svc.remove_document(task_id, doc_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return {"removed": True, "doc_id": doc_id}


# ── CLIENTES ──────────────────────────────────────────────────────────

@router.get("/clients/list", summary="Listar clientes disponíveis")
def list_clients():
    clients = repo.list_clients()
    return [
        {
            "id":           c.id,
            "company_name": c.company_name,
            "cnpj":         c.mask_cnpj(),
            "email":        c.email,
            "responsible":  c.responsible,
            "department":   c.department,
        }
        for c in clients
    ]


# ── HELPER ────────────────────────────────────────────────────────────

def _extract_text(path: str) -> str:
    try:
        import fitz
        doc  = fitz.open(path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        return ""

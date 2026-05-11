"""
Router: /emails
Histórico de envios com download de PDF.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os

from app.repositories.mock_repository import MockRepository

router = APIRouter()
repo:  MockRepository = None


@router.get("/logs", summary="Listar histórico de envios")
def list_logs(
    client_id:  Optional[str] = None,
    task_name:  Optional[str] = None,
    status:     Optional[str] = None,
    department: Optional[str] = None,
):
    logs = repo.list_all_logs()
    if client_id:  logs = [l for l in logs if l.client_id  == client_id]
    if task_name:  logs = [l for l in logs if task_name.lower() in l.task_name.lower()]
    if status:     logs = [l for l in logs if l.status.value == status.upper()]
    if department: logs = [l for l in logs if l.department  == department.upper()]
    return [l.summary() for l in logs]


@router.get("/logs/{log_id}", summary="Buscar log de envio por ID")
def get_log(log_id: str):
    log = repo._email_logs.get(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log não encontrado.")
    return log.summary()


@router.get("/logs/{log_id}/download", summary="Baixar PDF de um envio do histórico")
def download_pdf(log_id: str):
    """
    Retorna o arquivo PDF vinculado ao log para download.
    O arquivo fica armazenado em historico/pdfs/ no servidor.
    """
    log = repo._email_logs.get(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log não encontrado.")
    if not log.document_stored_path or not os.path.exists(log.document_stored_path):
        raise HTTPException(status_code=404, detail="Arquivo não disponível no servidor.")
    return FileResponse(
        path=log.document_stored_path,
        filename=log.document_filename,
        media_type="application/pdf",
    )


@router.get("/logs/client/{client_id}", summary="Histórico de envios de uma empresa")
def logs_by_client(client_id: str):
    return [l.summary() for l in repo.get_logs_by_client(client_id)]

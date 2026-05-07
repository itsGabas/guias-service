from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.email_service import EmailService
from app.services.task_service import TaskService
from app.repositories.mock_repository import MockRepository

router:    APIRouter       = APIRouter()
email_svc: EmailService    = None   # injetado pelo main.py
task_svc:  TaskService     = None
repo:      MockRepository  = None


# ── SCHEMAS ───────────────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    task_id:  str
    sent_by:  str


# ── ENDPOINTS ─────────────────────────────────────────────────────────

@router.post("/send", summary="Disparar envio de e-mail para uma tarefa")
def send_email(body: SendEmailRequest):
    try:
        task = task_svc.get_task(body.task_id)
        log  = email_svc.send_task(task, sent_by=body.sent_by)
        return log.summary()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no envio: {str(e)}")


@router.get("/logs", summary="Listar todos os logs de envio")
def list_logs():
    return [l.summary() for l in repo.list_all_logs()]


@router.get("/logs/task/{task_id}", summary="Logs de envio de uma tarefa específica")
def logs_by_task(task_id: str):
    logs = repo.get_logs_by_task(task_id)
    if not logs:
        return []
    return [l.summary() for l in logs]


@router.get("/logs/client/{client_id}", summary="Histórico de envios de um cliente")
def logs_by_client(client_id: str):
    return [l.summary() for l in repo.get_logs_by_client(client_id)]

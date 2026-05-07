"""
GUIAS SERVICE — API REST
Execute: uvicorn app.main:app --reload
Docs:    http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import tasks, emails
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService
from app.services.task_service import TaskService
from app.services.email_service import EmailService
from mock_data.clients import MOCK_CLIENTS

# ── Inicializa dependências ────────────────────────────────────────────
repo      = MockRepository()
pdf_svc   = PDFService()
task_svc  = TaskService(repo, pdf_svc)
email_svc = EmailService(repo)

# Carrega clientes mock (substitui por Supabase futuramente)
for client in MOCK_CLIENTS:
    repo.save_client(client)

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Guias Service",
    description="API para criação de tarefas e envio de guias aos clientes",
    version="1.0.0",
)

# ── CORS — permite o Node.js chamar esta API ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restringe pro domínio da Vercel em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Injeta dependências nos routers ───────────────────────────────────
tasks.task_svc  = task_svc
tasks.repo      = repo
emails.email_svc = email_svc
emails.task_svc  = task_svc
emails.repo      = repo

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(tasks.router,  prefix="/tasks",  tags=["Tarefas"])
app.include_router(emails.router, prefix="/emails", tags=["E-mails"])

# ── Health check ──────────────────────────────────────────────────────
@app.get("/", tags=["Status"])
def health_check():
    return {
        "status": "online",
        "service": "guias-service",
        "version": "1.0.0",
    }

@app.get("/stats", tags=["Status"])
def stats():
    return repo.stats()

"""
GUIAS SERVICE — API REST
Execute: python -m uvicorn app.main:app --reload
Docs:    http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import tasks, emails, clients, templates
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService
from app.services.xlsx_service import XlsxService

# ── Instâncias globais (substituídas por Supabase futuramente) ────────
repo     = MockRepository()
pdf_svc  = PDFService()
xlsx_svc = XlsxService()

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Guias Service",
    description="API para criação de templates, envio de guias e histórico por empresa/departamento",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restringir pro domínio da Vercel em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Injeta dependências nos routers ───────────────────────────────────
clients.repo     = repo
clients.xlsx_svc = xlsx_svc

templates.repo    = repo
templates.pdf_svc = pdf_svc

tasks.repo    = repo
tasks.pdf_svc = pdf_svc

emails.repo = repo

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(clients.router,   prefix="/clients",   tags=["Empresas"])
app.include_router(templates.router, prefix="/templates", tags=["Templates"])
app.include_router(tasks.router,     prefix="/tasks",     tags=["Tarefas & PDFs"])
app.include_router(emails.router,    prefix="/emails",    tags=["E-mails & Histórico"])

# ── Status ────────────────────────────────────────────────────────────
@app.get("/", tags=["Status"])
def health_check():
    return {"status": "online", "service": "guias-service", "version": "2.0.0"}

@app.get("/stats", tags=["Status"])
def stats():
    return repo.stats()

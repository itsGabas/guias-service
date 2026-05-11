"""
Router: /tasks
Upload de PDFs, vinculação com template/empresa e disparo de envio.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import uuid, shutil, tempfile, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

from app.models.email_log import EmailLog, EmailStatus
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService

router   = APIRouter()
repo:     MockRepository = None
pdf_svc:  PDFService     = None

HISTORICO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "historico", "pdfs")
os.makedirs(HISTORICO_DIR, exist_ok=True)

# Configurações SMTP — virão do .env / Supabase futuramente
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.getenv("GMAIL_REMETENTE", "")
SMTP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


# ── SCHEMAS ───────────────────────────────────────────────────────────

class SendRequest(BaseModel):
    client_id:   str
    template_id: str
    competence:  str
    sent_by:     str
    filenames:   list[str]   # nomes dos arquivos já enviados via /tasks/upload


# ── UPLOAD DE PDF ─────────────────────────────────────────────────────

@router.post("/upload", summary="Fazer upload de PDF e receber dados extraídos + validação")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF, extrai dados, identifica empresa e template automaticamente.
    Retorna tudo que o frontend precisa para montar a tela de confirmação.
    Não envia nada — apenas analisa.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas PDFs são aceitos.")

    contents = await file.read()
    size_kb  = len(contents) / 1024

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
                "id":            c.id,
                "codigo":        c.codigo,
                "company_name":  c.company_name,
                "cnpj":          c.mask_cnpj(),
                "matched_by":    extracao.client_match.matched_by,
                "matched_value": extracao.client_match.matched_value,
            }

        # Calcula destinatários e motivos de bloqueio
        bloqueios = []
        destinatarios = []
        if not template:
            n = len(repo.list_templates())
            bloqueios.append(f"Nenhuma tarefa reconheceu este PDF ({n} template(s) testado(s))")
        elif not client_info:
            bloqueios.append("Empresa não identificada — selecionar manualmente")
        else:
            c   = extracao.client_match.client
            dept = template.department.value
            destinatarios = c.get_emails_for_department(dept)
            if not c.emails:
                bloqueios.append("Empresa sem nenhum e-mail cadastrado")
            elif not destinatarios:
                todos = [ce.email for ce in c.emails]
                bloqueios.append(f"Nenhum e-mail configurado para {dept} — existentes: {', '.join(todos)}")

        # Salva cópia temporária para envio posterior
        stored_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        stored_path = os.path.join(HISTORICO_DIR, stored_name)
        shutil.copy2(tmp_path, stored_path)

        return {
            "filename":      file.filename,
            "stored_name":   stored_name,   # usar no /tasks/send
            "size_kb":       round(size_kb, 1),
            "confidence":    round(extracao.confidence, 2),
            "extracted": {
                "competence": extracao.suggested_competence,
                "cnpj":       extracao.suggested_company_cnpj,
                "ie":         extracao.suggested_company_ie,
            },
            "client":        client_info,
            "template":      template.summary() if template else None,
            "recipients":    destinatarios,
            "can_send":      len(bloqueios) == 0,
            "block_reasons": bloqueios,
            "warnings":      extracao.warnings,
        }
    finally:
        os.unlink(tmp_path)


# ── ENVIO ─────────────────────────────────────────────────────────────

@router.post("/send", summary="Disparar envio de PDFs já analisados")
def send_pdfs(body: SendRequest):
    """
    Envia os PDFs para os e-mails configurados no departamento do template.
    Os arquivos devem ter sido previamente enviados via /tasks/upload.
    """
    client   = repo.get_client(body.client_id)
    template = repo.get_template(body.template_id)

    if not client:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado.")

    dept         = template.department.value
    destinatarios = client.get_emails_for_department(dept)

    if not destinatarios:
        raise HTTPException(status_code=400,
            detail=f"Nenhum e-mail configurado para o departamento {dept} nesta empresa.")

    resultados = []
    for stored_name in body.filenames:
        stored_path = os.path.join(HISTORICO_DIR, stored_name)
        if not os.path.exists(stored_path):
            resultados.append({"file": stored_name, "status": "ERRO", "detail": "Arquivo não encontrado no servidor"})
            continue
        try:
            _enviar_smtp(stored_path, stored_name, client, template, destinatarios, body.competence)
            log = _registrar_log(
                task_name=template.name, client=client, filename=stored_name,
                stored_path=stored_path, recipients=destinatarios,
                department=dept, sent_by=body.sent_by,
                competence=body.competence, status=EmailStatus.ENVIADO,
            )
            resultados.append({"file": stored_name, "status": "ENVIADO", "log_id": log.id, "recipients": destinatarios})
        except Exception as e:
            _registrar_log(
                task_name=template.name, client=client, filename=stored_name,
                stored_path=stored_path, recipients=destinatarios,
                department=dept, sent_by=body.sent_by,
                competence=body.competence, status=EmailStatus.FALHOU, error=str(e),
            )
            resultados.append({"file": stored_name, "status": "ERRO", "detail": str(e)})

    return {"results": resultados, "total": len(resultados),
            "sent": sum(1 for r in resultados if r["status"] == "ENVIADO")}


# ── HELPERS ───────────────────────────────────────────────────────────

def _enviar_smtp(path, filename, client, template, destinatarios, competence):
    dept = template.department.value
    msg  = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(destinatarios)
    msg["Subject"] = f"[{dept}] {template.name} — {client.company_name} — {competence}"
    corpo = (
        f"Prezado(a),\n\nSegue em anexo o documento referente à competência {competence}.\n\n"
        f"Empresa  : {client.company_name}\nCNPJ     : {client.mask_cnpj()}\n"
        f"Depto    : {dept}\nDocumento: {filename}\n\n"
        f"Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n"
    )
    msg.attach(MIMEText(corpo, "plain", "utf-8"))
    with open(path, "rb") as f:
        p = MIMEApplication(f.read(), _subtype="pdf")
        p.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(p)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo(); s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(SMTP_USER, destinatarios, msg.as_string())


def _registrar_log(task_name, client, filename, stored_path,
                   recipients, department, sent_by, competence, status, error=None):
    log = EmailLog(
        id=str(uuid.uuid4())[:8],
        task_name=task_name,
        client_id=client.id,
        client_name=client.company_name,
        document_filename=filename,
        document_stored_path=stored_path,
        recipients=recipients,
        department=department,
        sent_by=sent_by,
        competence=competence,
        status=status,
        error_message=error,
    )
    repo.save_email_log(log)
    return log

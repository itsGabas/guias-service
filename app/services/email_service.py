import uuid
from datetime import datetime
from typing import Optional

from app.models.task import Task
from app.models.client import Client
from app.models.email_log import EmailLog, EmailStatus
from app.models.enums import TaskStatus
from app.repositories.mock_repository import MockRepository


class EmailService:
    """
    Responsável por:
    - Validar pré-condições antes do envio
    - Simular (mock) ou executar o envio real de e-mail
    - Registrar LOG detalhado de cada tentativa
    - Atualizar status da tarefa após envio

    Para integrar com Resend/SendGrid no futuro,
    basta implementar _send_real() e chavear pela variável USE_REAL_SMTP.
    """

    USE_REAL_SMTP = False   # Muda para True quando tiver credenciais

    def __init__(self, repository: MockRepository):
        self.repo = repository

    def send_task(self, task: Task, sent_by: str) -> EmailLog:
        """
        Ponto de entrada principal.
        Valida, envia (ou simula), loga e atualiza o status da tarefa.
        """
        # 1. Valida se pode enviar
        can_send, reason = task.can_send()
        if not can_send:
            raise ValueError(f"Envio bloqueado: {reason}")

        # 2. Busca dados do cliente
        client = self.repo.get_client(task.client_id)
        if not client:
            raise ValueError(f"Cliente '{task.client_id}' não encontrado no repositório.")
        if not client.email:
            raise ValueError(f"Cliente '{client.company_name}' não possui e-mail cadastrado.")

        # 3. Monta conteúdo do e-mail
        subject = self._build_subject(task, client)
        body = self._build_body(task, client)
        attachments = [doc.filename for doc in task.documents]

        # 4. Tenta enviar
        try:
            if self.USE_REAL_SMTP:
                message_id = self._send_real(
                    to_email=client.email,
                    to_name=client.company_name,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                )
            else:
                message_id = self._send_mock(
                    to_email=client.email,
                    subject=subject,
                    attachments=attachments,
                )

            # 5. Log de sucesso
            log = self._create_log(
                task=task,
                client=client,
                subject=subject,
                sent_by=sent_by,
                attachments=attachments,
                status=EmailStatus.SIMULADO if not self.USE_REAL_SMTP else EmailStatus.ENVIADO,
                message_id=message_id,
            )

            # 6. Atualiza status da tarefa
            task.mark_as_sent()
            self.repo.save_task(task)

        except Exception as e:
            # Log de falha
            log = self._create_log(
                task=task,
                client=client,
                subject=subject,
                sent_by=sent_by,
                attachments=attachments,
                status=EmailStatus.FALHOU,
                error_message=str(e),
            )
            print(f"[EMAIL FALHOU] {e}")

        self.repo.save_email_log(log)
        self._print_log(log)
        return log

    # ── CONSTRUTORES DE CONTEÚDO ──────────────────────────────────────

    def _build_subject(self, task: Task, client: Client) -> str:
        return f"[{task.department.value}] {task.title} — Competência: {task.competence}"

    def _build_body(self, task: Task, client: Client) -> str:
        doc_list = "\n".join(
            f"  - {doc.document_type.value}: {doc.filename}" for doc in task.documents
        )
        return (
            f"Prezado(a) {client.company_name},\n\n"
            f"Segue(m) em anexo o(s) documento(s) referente(s) à competência {task.competence}:\n\n"
            f"{doc_list}\n\n"
            f"Qualquer dúvida, entre em contato com nosso escritório.\n\n"
            f"Atenciosamente,\n"
            f"Departamento de {task.department.value}"
        )

    # ── ENVIO ─────────────────────────────────────────────────────────

    def _send_mock(self, to_email: str, subject: str, attachments: list[str]) -> str:
        """Simula o envio sem SMTP real. Retorna um message_id fictício."""
        mock_id = f"mock-{uuid.uuid4().hex[:12]}"
        print(f"\n{'='*55}")
        print(f"  📧 SIMULAÇÃO DE ENVIO DE E-MAIL")
        print(f"{'='*55}")
        print(f"  Para     : {to_email}")
        print(f"  Assunto  : {subject}")
        print(f"  Anexos   : {', '.join(attachments)}")
        print(f"  Mock ID  : {mock_id}")
        print(f"{'='*55}\n")
        return mock_id

    def _send_real(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        attachments: list[str],
    ) -> str:
        """
        Implementação real com Resend.
        Descomente e configure quando tiver a chave de API.

        import resend
        resend.api_key = os.environ["RESEND_API_KEY"]

        params = {
            "from": "escritorio@seudominio.com.br",
            "to": [to_email],
            "subject": subject,
            "text": body,
            # attachments: montar com bytes dos PDFs
        }
        response = resend.Emails.send(params)
        return response["id"]
        """
        raise NotImplementedError("Envio real ainda não configurado. USE_REAL_SMTP = False")

    # ── LOG ───────────────────────────────────────────────────────────

    def _create_log(
        self,
        task: Task,
        client: Client,
        subject: str,
        sent_by: str,
        attachments: list[str],
        status: EmailStatus,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> EmailLog:
        return EmailLog(
            id=str(uuid.uuid4())[:8],
            task_id=task.id,
            client_id=client.id,
            recipient_email=client.email,
            recipient_name=client.company_name,
            subject=subject,
            sent_by=sent_by,
            documents_sent=attachments,
            status=status,
            message_id=message_id,
            error_message=error_message,
        )

    def _print_log(self, log: EmailLog) -> None:
        status_icon = {"ENVIADO": "✅", "SIMULADO": "🔵", "FALHOU": "❌"}.get(log.status.value, "?")
        print(f"[EMAIL LOG] {status_icon} {log}")
        for k, v in log.summary().items():
            print(f"  {k}: {v}")

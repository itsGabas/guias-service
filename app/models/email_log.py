from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class EmailStatus(str, Enum):
    ENVIADO = "ENVIADO"
    FALHOU = "FALHOU"
    SIMULADO = "SIMULADO"       # usado nos testes sem banco/SMTP real


@dataclass
class EmailLog:
    id: str
    task_id: str
    client_id: str
    recipient_email: str
    recipient_name: str
    subject: str
    sent_by: str                 # funcionário que disparou
    documents_sent: List[str]    # lista de filenames enviados
    status: EmailStatus
    sent_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    message_id: Optional[str] = None    # ID retornado pelo provedor (Resend/SendGrid)

    def __repr__(self) -> str:
        return (
            f"<EmailLog [{self.status.value}] "
            f"→ {self.recipient_email} | Task: {self.task_id} | "
            f"{self.sent_at.strftime('%d/%m/%Y %H:%M:%S')}>"
        )

    def summary(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "client_id": self.client_id,
            "recipient": self.recipient_email,
            "subject": self.subject,
            "sent_by": self.sent_by,
            "documents": self.documents_sent,
            "status": self.status.value,
            "sent_at": self.sent_at.isoformat(),
            "error": self.error_message,
            "provider_message_id": self.message_id,
        }

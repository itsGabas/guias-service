from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class EmailStatus(str, Enum):
    ENVIADO  = "ENVIADO"
    FALHOU   = "FALHOU"
    SIMULADO = "SIMULADO"


@dataclass
class EmailLog:
    id: str
    task_name: str                   # nome da tarefa/template
    client_id: str
    client_name: str
    document_filename: str           # nome original do arquivo
    document_stored_path: str        # caminho salvo em historico/pdfs/
    recipients: list[str]            # e-mails que receberam
    department: str
    sent_by: str                     # quem enviou (login futuro)
    competence: str
    status: EmailStatus
    sent_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

    def sent_at_formatted(self) -> str:
        return self.sent_at.strftime("%d/%m/%Y %H:%M:%S")

    def summary(self) -> dict:
        return {
            "id":                self.id,
            "task_name":         self.task_name,
            "client_name":       self.client_name,
            "document":          self.document_filename,
            "stored_path":       self.document_stored_path,
            "recipients":        self.recipients,
            "department":        self.department,
            "sent_by":           self.sent_by,
            "competence":        self.competence,
            "status":            self.status.value,
            "sent_at":           self.sent_at_formatted(),
            "error":             self.error_message,
        }

    def __repr__(self):
        return (f"<EmailLog [{self.status.value}] {self.document_filename} "
                f"→ {self.recipients} | {self.sent_at_formatted()}>")

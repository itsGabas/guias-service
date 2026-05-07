from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from app.models.enums import TaskStatus, Department
from app.models.document import Document


@dataclass
class Task:
    id: str
    title: str
    client_id: str
    competence: str              # ex: "Janeiro/2026"
    department: Department
    created_by: str              # nome do funcionário que criou
    documents: List[Document] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDENTE
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ── Regras de negócio ─────────────────────────────────────────────

    def add_document(self, doc: Document) -> None:
        self.documents.append(doc)

    def remove_document(self, doc_id: str) -> bool:
        before = len(self.documents)
        self.documents = [d for d in self.documents if d.id != doc_id]
        return len(self.documents) < before

    def all_documents_confirmed(self) -> bool:
        if not self.documents:
            return False
        return all(d.confirmed for d in self.documents)

    def can_send(self) -> tuple[bool, str]:
        """Valida se a tarefa está pronta para envio."""
        if not self.documents:
            return False, "Nenhum documento adicionado à tarefa."
        if not self.all_documents_confirmed():
            pending = [d.filename for d in self.documents if not d.confirmed]
            return False, f"Documentos aguardando confirmação: {', '.join(pending)}"
        if self.status == TaskStatus.ENVIADA:
            return False, "Tarefa já foi enviada."
        if self.status == TaskStatus.CONCLUIDA:
            return False, "Tarefa já está concluída."
        return True, "OK"

    def mark_as_sent(self) -> None:
        self.status = TaskStatus.ENVIADA
        self.sent_at = datetime.now()

    def mark_as_completed(self) -> None:
        self.status = TaskStatus.CONCLUIDA
        self.completed_at = datetime.now()

    def document_count(self) -> int:
        return len(self.documents)

    def total_size_kb(self) -> float:
        return sum(d.file_size_kb for d in self.documents)

    def __repr__(self) -> str:
        return (
            f"<Task '{self.title}' | {self.status.value} | "
            f"{self.document_count()} doc(s) | Cliente: {self.client_id}>"
        )

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "client_id": self.client_id,
            "competence": self.competence,
            "department": self.department.value,
            "status": self.status.value,
            "documents": [d.summary() for d in self.documents],
            "all_confirmed": self.all_documents_confirmed(),
            "total_size_kb": self.total_size_kb(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

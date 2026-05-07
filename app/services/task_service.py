import uuid
from datetime import datetime
from typing import List, Optional

from app.models.enums import DocumentType, Department, TaskStatus
from app.models.task import Task
from app.models.document import Document
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService


class TaskService:
    """
    Orquestra a criação, gerenciamento e ciclo de vida das tarefas.
    Depende do repositório (injeção de dependência) para facilitar
    a troca de MockRepository → SupabaseRepository no futuro.
    """

    def __init__(self, repository: MockRepository, pdf_service: PDFService):
        self.repo = repository
        self.pdf_service = pdf_service

    # ── CRIAÇÃO ───────────────────────────────────────────────────────

    def create_task(
        self,
        title: str,
        client_id: str,
        competence: str,
        department: Department,
        created_by: str,
        notes: Optional[str] = None,
    ) -> Task:
        client = self.repo.get_client(client_id)
        if not client:
            raise ValueError(f"Cliente '{client_id}' não encontrado.")

        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            client_id=client_id,
            competence=competence,
            department=department,
            created_by=created_by,
            notes=notes,
        )
        self.repo.save_task(task)
        print(f"[TASK CRIADA] {task}")
        return task

    # ── DOCUMENTOS ────────────────────────────────────────────────────

    def add_document_from_text(
        self,
        task_id: str,
        filename: str,
        file_size_kb: float,
        raw_text: str,
        file_path: str = "mock/path",
        # Valores que o usuário pode informar manualmente
        manual_type: Optional[DocumentType] = None,
        manual_competence: Optional[str] = None,
    ) -> Document:
        """
        Fluxo híbrido:
        1. Tenta extrair tipo e competência do texto do PDF
        2. Mescla com o que o usuário informou manualmente
        3. Adiciona documento à tarefa (ainda não confirmado)
        """
        task = self._get_task_or_raise(task_id)

        extraction = self.pdf_service.extract_from_text(raw_text)

        # Usa o manual se informado, senão usa o extraído
        final_type = manual_type or extraction.suggested_type or DocumentType.OUTRO
        final_competence = manual_competence or extraction.suggested_competence or task.competence

        doc = Document(
            id=str(uuid.uuid4())[:8],
            filename=filename,
            file_size_kb=file_size_kb,
            document_type=final_type,
            competence=final_competence,
            file_path=file_path,
            extracted_company=extraction.suggested_company_cnpj,
            extracted_competence=extraction.suggested_competence,
            extracted_type=extraction.suggested_type.value if extraction.suggested_type else None,
            confirmed=False,
        )

        task.add_document(doc)
        self.repo.save_task(task)

        print(f"[DOCUMENTO ADICIONADO] {doc}")
        if extraction.warnings:
            for w in extraction.warnings:
                print(f"  ⚠ {w}")
        print(f"  Confiança da leitura automática: {extraction.confidence:.0%}")

        return doc

    def confirm_document(self, task_id: str, doc_id: str) -> Document:
        """Usuário revisou e confirmou os dados do documento."""
        task = self._get_task_or_raise(task_id)
        doc = self._get_doc_or_raise(task, doc_id)
        doc.confirmed = True
        self.repo.save_task(task)
        print(f"[DOCUMENTO CONFIRMADO] {doc}")
        return doc

    def remove_document(self, task_id: str, doc_id: str) -> bool:
        task = self._get_task_or_raise(task_id)
        removed = task.remove_document(doc_id)
        if removed:
            self.repo.save_task(task)
            print(f"[DOCUMENTO REMOVIDO] doc_id={doc_id} da task_id={task_id}")
        return removed

    # ── CONSULTAS ─────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> Task:
        return self._get_task_or_raise(task_id)

    def list_tasks(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Task]:
        return self.repo.list_tasks(client_id=client_id, status=status, department=department)

    def list_pending_tasks(self) -> List[Task]:
        return self.repo.list_tasks(status=TaskStatus.PENDENTE.value)

    # ── PRIVADOS ──────────────────────────────────────────────────────

    def _get_task_or_raise(self, task_id: str) -> Task:
        task = self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Tarefa '{task_id}' não encontrada.")
        return task

    def _get_doc_or_raise(self, task: Task, doc_id: str) -> Document:
        for doc in task.documents:
            if doc.id == doc_id:
                return doc
        raise ValueError(f"Documento '{doc_id}' não encontrado na tarefa '{task.id}'.")

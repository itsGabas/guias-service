from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from app.models.enums import DocumentType


@dataclass
class Document:
    id: str
    filename: str
    file_size_kb: float
    document_type: DocumentType
    competence: str              # ex: "Janeiro/2026"
    file_path: str               # path local ou URL futura do Supabase Storage

    # Extraído automaticamente via PDF (pode ser None se leitura falhar)
    extracted_company: Optional[str] = None
    extracted_competence: Optional[str] = None
    extracted_type: Optional[str] = None

    # Confirmado manualmente pelo usuário
    confirmed: bool = False
    uploaded_at: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        return (
            f"<Document [{self.document_type.value}] "
            f"{self.competence} | {self.filename} | "
            f"{'✓ Confirmado' if self.confirmed else '⚠ Pendente confirmação'}>"
        )

    def summary(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "type": self.document_type.value,
            "competence": self.competence,
            "confirmed": self.confirmed,
            "extracted": {
                "company": self.extracted_company,
                "competence": self.extracted_competence,
                "type": self.extracted_type,
            }
        }

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from app.models.enums import Department


@dataclass
class TaskTemplate:
    """
    Define um modelo de tarefa com regras de conteúdo.
    Qualquer PDF que contenha TODAS as keywords será vinculado a este template.
    """
    id: str
    name: str
    department: Department
    keywords: list[str]                  # todas obrigatórias (AND)
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    validated: bool = False              # True se foi validado com PDF modelo
    model_filename: Optional[str] = None # nome do PDF usado como modelo

    def matches(self, text: str) -> tuple[bool, list[str], list[str]]:
        """
        Verifica se um texto de PDF bate com todas as keywords.
        Retorna: (bateu, keywords_encontradas, keywords_faltando)
        """
        text_lower = text.lower()
        encontradas = [kw for kw in self.keywords if kw.lower() in text_lower]
        faltando    = [kw for kw in self.keywords if kw.lower() not in text_lower]
        return len(faltando) == 0, encontradas, faltando

    def summary(self) -> dict:
        return {
            "id":             self.id,
            "name":           self.name,
            "department":     self.department.value,
            "keywords":       self.keywords,
            "validated":      self.validated,
            "model_filename": self.model_filename,
            "created_by":     self.created_by,
            "created_at":     self.created_at.isoformat(),
        }

    def __repr__(self):
        status = "✓ validado" if self.validated else "⚠ não validado"
        return f"<TaskTemplate '{self.name}' | {len(self.keywords)} regras | {status}>"

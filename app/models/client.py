from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class ClientEmail:
    """E-mail vinculado a um cliente com lista de departamentos que pode receber."""
    email: str
    label: str                          # ex: "Financeiro", "Contador", "Sócio"
    departments: list[str] = field(default_factory=list)  # ex: ["RH", "FISCAL"]

    def receives(self, department: str) -> bool:
        """Verifica se este e-mail recebe guias do departamento informado."""
        return department.upper() in [d.upper() for d in self.departments]

    def __repr__(self):
        deptos = ", ".join(self.departments) if self.departments else "nenhum"
        return f"<ClientEmail {self.email} [{self.label}] → {deptos}>"


@dataclass
class Client:
    id: str
    company_name: str
    cnpj: str
    codigo: Optional[str] = None
    emails: list[ClientEmail] = field(default_factory=list)
    responsible: Optional[str] = None
    department: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    phone: Optional[str] = None
    active: bool = True

    # ── Helpers de e-mail ─────────────────────────────────────────────

    def get_emails_for_department(self, department: str) -> list[str]:
        """Retorna lista de endereços que recebem deste departamento."""
        return [ce.email for ce in self.emails if ce.receives(department)]

    def add_email(self, email: str, label: str, departments: list[str]) -> "ClientEmail":
        ce = ClientEmail(email=email.strip().lower(), label=label.strip(), departments=departments)
        self.emails.append(ce)
        return ce

    def remove_email(self, email: str) -> bool:
        before = len(self.emails)
        self.emails = [ce for ce in self.emails if ce.email != email.lower()]
        return len(self.emails) < before

    # ── Helpers de identificação ──────────────────────────────────────

    def __repr__(self) -> str:
        ie = f" | IE: {self.inscricao_estadual}" if self.inscricao_estadual else ""
        return f"<Client [{self.codigo}] {self.company_name} | {self.cnpj}{ie}>"

    def mask_cnpj(self) -> str:
        digits = self.cnpj_digits()
        if len(digits) == 14:
            return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return self.cnpj

    def cnpj_digits(self) -> str:
        return re.sub(r'\D', '', self.cnpj or '')

    def ie_digits(self) -> Optional[str]:
        if not self.inscricao_estadual:
            return None
        return re.sub(r'\D', '', self.inscricao_estadual)

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class Client:
    id: str
    company_name: str
    cnpj: str
    email: str
    responsible: str
    department: str
    inscricao_estadual: Optional[str] = None   # IE — formato livre por estado
    phone: Optional[str] = None
    active: bool = True

    def __repr__(self) -> str:
        ie = f" | IE: {self.inscricao_estadual}" if self.inscricao_estadual else ""
        return f"<Client {self.company_name} | {self.cnpj}{ie} | {self.email}>"

    def mask_cnpj(self) -> str:
        digits = re.sub(r'\D', '', self.cnpj)
        if len(digits) != 14:
            return self.cnpj
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

    def cnpj_digits(self) -> str:
        """CNPJ só com dígitos para comparação."""
        return re.sub(r'\D', '', self.cnpj)

    def ie_digits(self) -> Optional[str]:
        """IE só com dígitos para comparação (ignora pontos, barras, traços)."""
        if not self.inscricao_estadual:
            return None
        return re.sub(r'\D', '', self.inscricao_estadual)

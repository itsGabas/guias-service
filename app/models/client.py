from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Client:
    id: str
    company_name: str
    cnpj: str
    email: str
    responsible: str             # responsável no escritório
    department: str              # departamento dono do cliente
    phone: Optional[str] = None
    active: bool = True

    def __repr__(self) -> str:
        return f"<Client {self.company_name} | {self.cnpj} | {self.email}>"

    def mask_cnpj(self) -> str:
        """Retorna CNPJ formatado: 00.000.000/0001-00"""
        digits = self.cnpj.replace(".", "").replace("/", "").replace("-", "")
        if len(digits) != 14:
            return self.cnpj
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

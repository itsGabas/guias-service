import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from app.models.enums import DocumentType

if TYPE_CHECKING:
    from app.models.client import Client

# ── Mapeamento tipo → palavras-chave ──────────────────────────────────
KEYWORD_MAP: dict[DocumentType, list[str]] = {
    DocumentType.HOLERITE:         ["holerite", "contracheque", "recibo de pagamento", "folha de pagamento"],
    DocumentType.EXTRATO_MENSAL:   ["extrato", "extrato mensal", "extrato bancário", "movimentação"],
    DocumentType.DARF:             ["darf", "documento de arrecadação", "receita federal"],
    DocumentType.GUIA_FGTS:       ["fgts", "guia de recolhimento", "fundo de garantia"],
    DocumentType.SIMPLES_NACIONAL: ["simples nacional", "das", "pgmei", "simei"],
    DocumentType.CONTRATO_SOCIAL:  ["contrato social", "estatuto social", "ata de constituição"],
    DocumentType.BALANCETE:        ["balancete", "balanço", "demonstração"],
    DocumentType.DECLARACAO_IR:    ["irpf", "irpj", "declaração de imposto", "imposto de renda"],
}

COMPETENCE_PATTERNS = [
    r'\b(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)[\/\-\s]\d{2,4}\b',
    r'\b\d{2}[\/\-]\d{4}\b',
    r'\bcompetência[:\s]+(.+)',
    r'\bref(?:erente)?[\.:\s]+(.+)',
]

MONTH_NAMES = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril",   "05": "Maio",      "06": "Junho",
    "07": "Julho",   "08": "Agosto",    "09": "Setembro",
    "10": "Outubro", "11": "Novembro",  "12": "Dezembro",
}

CNPJ_PATTERN = re.compile(r'\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[-\s]?\d{2}')

# Rótulos que precedem a IE no PDF (case-insensitive)
IE_LABELS = [
    r'insc(?:rição|r\.?)?\s*estadual[:\s#]*',
    r'i\.?\s*e\.?[:\s#]+',
    r'ie[:\s#]+',
    r'inscrição\s*est\.?[:\s#]*',
]


@dataclass
class ClientMatch:
    """Resultado da tentativa de identificar o cliente no PDF."""
    client: Optional["Client"]
    matched_by: Optional[str]   # "cnpj", "ie", ou None
    matched_value: Optional[str]


@dataclass
class PDFExtraction:
    """Resultado completo da leitura e análise de um PDF."""
    raw_text: str
    suggested_type: Optional[DocumentType]
    suggested_competence: Optional[str]
    suggested_company_cnpj: Optional[str]
    suggested_company_ie: Optional[str]
    client_match: Optional[ClientMatch]
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def is_reliable(self) -> bool:
        return self.confidence >= 0.6

    def identified_company(self) -> Optional[str]:
        """Retorna o identificador encontrado (CNPJ ou IE), independente do tipo."""
        return self.suggested_company_cnpj or self.suggested_company_ie

    def __repr__(self) -> str:
        id_str = self.identified_company() or "não identificado"
        return (
            f"<PDFExtraction type={self.suggested_type} "
            f"competence='{self.suggested_competence}' "
            f"company='{id_str}' confidence={self.confidence:.0%}>"
        )


class PDFService:
    """
    Lê PDFs e tenta identificar:
    - Tipo do documento (por palavras-chave)
    - Competência (por padrões de data)
    - Empresa (por CNPJ ou Inscrição Estadual)

    Suporta correspondência com base de clientes cadastrados
    para identificar empresa mesmo quando só a IE está no PDF.
    """

    def extract_from_file(self, file_path: str, clients: list = None) -> PDFExtraction:
        try:
            import fitz
            doc = fitz.open(file_path)
            raw_text = "".join(page.get_text() for page in doc)
            doc.close()
            return self._analyze(raw_text, clients or [])
        except ImportError:
            return self._empty_extraction(["PyMuPDF não instalado. Use: pip install pymupdf"])
        except Exception as e:
            return self._empty_extraction([f"Erro ao ler PDF: {str(e)}"])

    def extract_from_text(self, raw_text: str, clients: list = None) -> PDFExtraction:
        return self._analyze(raw_text, clients or [])

    # ── ANÁLISE PRINCIPAL ─────────────────────────────────────────────

    def _analyze(self, raw_text: str, clients: list) -> PDFExtraction:
        text_lower = raw_text.lower()
        warnings   = []

        suggested_type       = self._detect_type(text_lower)
        suggested_competence = self._detect_competence(text_lower)
        suggested_cnpj       = self._detect_cnpj(raw_text)
        suggested_ie         = self._detect_ie(raw_text) if not suggested_cnpj else None

        # Tenta casar com cliente da base
        client_match = self._match_client(raw_text, suggested_cnpj, suggested_ie, clients)

        # Confiança: tipo + competência + identificador da empresa
        has_company = bool(suggested_cnpj or suggested_ie or (client_match and client_match.client))
        hits = sum([suggested_type is not None, suggested_competence is not None, has_company])
        confidence = hits / 3.0

        if not suggested_type:
            warnings.append("Tipo do documento não identificado automaticamente.")
        if not suggested_competence:
            warnings.append("Competência não encontrada no texto do PDF.")
        if not suggested_cnpj and not suggested_ie:
            warnings.append("Nenhum identificador de empresa (CNPJ ou IE) encontrado no PDF.")
        elif suggested_ie and not suggested_cnpj:
            warnings.append(f"Documento usa Inscrição Estadual: {suggested_ie} (sem CNPJ).")

        return PDFExtraction(
            raw_text=raw_text,
            suggested_type=suggested_type,
            suggested_competence=suggested_competence,
            suggested_company_cnpj=suggested_cnpj,
            suggested_company_ie=suggested_ie,
            client_match=client_match,
            confidence=confidence,
            warnings=warnings,
        )

    # ── DETECÇÃO DE TIPO ──────────────────────────────────────────────

    def _detect_type(self, text_lower: str) -> Optional[DocumentType]:
        scores: dict[DocumentType, int] = {}
        for doc_type, keywords in KEYWORD_MAP.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[doc_type] = count
        return max(scores, key=lambda k: scores[k]) if scores else None

    # ── DETECÇÃO DE COMPETÊNCIA ───────────────────────────────────────

    def _detect_competence(self, text_lower: str) -> Optional[str]:
        for pattern in COMPETENCE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                found = match.group(0).strip()
                num_match = re.search(r'(\d{2})[\/\-](\d{4})', found)
                if num_match:
                    month_num, year = num_match.group(1), num_match.group(2)
                    month_name = MONTH_NAMES.get(month_num)
                    if month_name:
                        return f"{month_name}/{year}"
                return found.title()
        return None

    # ── DETECÇÃO DE CNPJ ──────────────────────────────────────────────

    def _detect_cnpj(self, raw_text: str) -> Optional[str]:
        match = CNPJ_PATTERN.search(raw_text)
        if match:
            digits = re.sub(r'\D', '', match.group(0))
            if len(digits) == 14:
                return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return None

    # ── DETECÇÃO DE IE ────────────────────────────────────────────────

    def _detect_ie(self, raw_text: str) -> Optional[str]:
        """
        Procura por rótulos de IE no texto e captura o valor logo após.
        Como o formato varia por estado, captura qualquer sequência
        alfanumérica após o rótulo identificado.
        """
        for label in IE_LABELS:
            pattern = label + r'([A-Z0-9][0-9A-Z\.\-\/]{4,19})'
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                ie_raw = match.group(1).strip()
                # Descarta se parecer CNPJ (14 dígitos) — já tratado acima
                if len(re.sub(r'\D', '', ie_raw)) == 14:
                    continue
                return ie_raw
        return None

    # ── CASAMENTO COM CLIENTE ─────────────────────────────────────────

    def _match_client(
        self,
        raw_text: str,
        cnpj: Optional[str],
        ie: Optional[str],
        clients: list,
    ) -> Optional[ClientMatch]:
        if not clients:
            return None

        text_clean = re.sub(r'\D', '', raw_text)

        # 1. Tenta por CNPJ
        if cnpj:
            cnpj_digits = re.sub(r'\D', '', cnpj)
            for client in clients:
                if client.cnpj_digits() == cnpj_digits:
                    return ClientMatch(client=client, matched_by="cnpj", matched_value=cnpj)

        # 2. Tenta por IE (compara dígitos cadastrados com dígitos do texto do PDF)
        for client in clients:
            ie_digits = client.ie_digits()
            if ie_digits and len(ie_digits) >= 5 and ie_digits in text_clean:
                return ClientMatch(
                    client=client,
                    matched_by="ie",
                    matched_value=client.inscricao_estadual,
                )

        # 3. IE detectada no PDF mas não bateu com nenhum cliente cadastrado
        if ie:
            return ClientMatch(client=None, matched_by=None, matched_value=ie)

        return ClientMatch(client=None, matched_by=None, matched_value=None)

    def _empty_extraction(self, warnings: list) -> PDFExtraction:
        return PDFExtraction(
            raw_text="", suggested_type=None, suggested_competence=None,
            suggested_company_cnpj=None, suggested_company_ie=None,
            client_match=None, confidence=0.0, warnings=warnings,
        )

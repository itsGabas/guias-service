import re
from dataclasses import dataclass
from typing import Optional
from app.models.enums import DocumentType


# Mapeamento de palavras-chave → tipo de documento
KEYWORD_MAP: dict[DocumentType, list[str]] = {
    DocumentType.HOLERITE:          ["holerite", "contracheque", "recibo de pagamento", "folha de pagamento"],
    DocumentType.EXTRATO_MENSAL:    ["extrato", "extrato mensal", "extrato bancário", "movimentação"],
    DocumentType.DARF:              ["darf", "documento de arrecadação", "receita federal"],
    DocumentType.GUIA_FGTS:        ["fgts", "guia de recolhimento", "fundo de garantia"],
    DocumentType.SIMPLES_NACIONAL:  ["simples nacional", "das", "pgmei", "simei"],
    DocumentType.CONTRATO_SOCIAL:   ["contrato social", "estatuto social", "ata de constituição"],
    DocumentType.BALANCETE:         ["balancete", "balanço", "demonstração"],
    DocumentType.DECLARACAO_IR:     ["irpf", "irpj", "declaração de imposto", "imposto de renda"],
}

# Padrões de competência: "Janeiro/2026", "01/2026", "Jan/26", etc.
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


@dataclass
class PDFExtraction:
    """Resultado da tentativa de leitura automática do PDF."""
    raw_text: str
    suggested_type: Optional[DocumentType]
    suggested_competence: Optional[str]
    suggested_company_cnpj: Optional[str]
    confidence: float               # 0.0 a 1.0
    warnings: list[str]

    def is_reliable(self) -> bool:
        return self.confidence >= 0.6

    def __repr__(self) -> str:
        return (
            f"<PDFExtraction type={self.suggested_type} "
            f"competence='{self.suggested_competence}' "
            f"confidence={self.confidence:.0%}>"
        )


class PDFService:
    """
    Serviço responsável por:
    1. Ler texto de um PDF (via PyMuPDF quando integrado)
    2. Tentar identificar tipo, competência e empresa automaticamente
    3. Retornar sugestão para o usuário confirmar/corrigir (fluxo híbrido)
    """

    def extract_from_file(self, file_path: str) -> PDFExtraction:
        """
        Lê o PDF real do disco usando PyMuPDF.
        Requer: pip install pymupdf
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()
            return self._analyze(raw_text)
        except ImportError:
            return PDFExtraction(
                raw_text="",
                suggested_type=None,
                suggested_competence=None,
                suggested_company_cnpj=None,
                confidence=0.0,
                warnings=["PyMuPDF não instalado. Use: pip install pymupdf"],
            )
        except Exception as e:
            return PDFExtraction(
                raw_text="",
                suggested_type=None,
                suggested_competence=None,
                suggested_company_cnpj=None,
                confidence=0.0,
                warnings=[f"Erro ao ler PDF: {str(e)}"],
            )

    def extract_from_text(self, raw_text: str) -> PDFExtraction:
        """
        Analisa texto já extraído (usado nos testes sem PDF real).
        """
        return self._analyze(raw_text)

    def _analyze(self, raw_text: str) -> PDFExtraction:
        text_lower = raw_text.lower()
        warnings = []

        suggested_type = self._detect_type(text_lower)
        suggested_competence = self._detect_competence(text_lower, raw_text)
        suggested_cnpj = self._detect_cnpj(raw_text)

        # Calcula confiança baseada no que foi encontrado
        hits = sum([
            suggested_type is not None,
            suggested_competence is not None,
            suggested_cnpj is not None,
        ])
        confidence = hits / 3.0

        if not suggested_type:
            warnings.append("Tipo do documento não identificado automaticamente.")
        if not suggested_competence:
            warnings.append("Competência não encontrada no texto do PDF.")
        if not suggested_cnpj:
            warnings.append("CNPJ da empresa não localizado no PDF.")

        return PDFExtraction(
            raw_text=raw_text,
            suggested_type=suggested_type,
            suggested_competence=suggested_competence,
            suggested_company_cnpj=suggested_cnpj,
            confidence=confidence,
            warnings=warnings,
        )

    def _detect_type(self, text_lower: str) -> Optional[DocumentType]:
        scores: dict[DocumentType, int] = {}
        for doc_type, keywords in KEYWORD_MAP.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[doc_type] = count
        if not scores:
            return None
        return max(scores, key=lambda k: scores[k])

    def _detect_competence(self, text_lower: str, raw_text: str) -> Optional[str]:
        for pattern in COMPETENCE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                found = match.group(0).strip()
                # Normaliza "01/2026" → "Janeiro/2026"
                num_match = re.search(r'(\d{2})[\/\-](\d{4})', found)
                if num_match:
                    month_num, year = num_match.group(1), num_match.group(2)
                    month_name = MONTH_NAMES.get(month_num)
                    if month_name:
                        return f"{month_name}/{year}"
                return found.title()
        return None

    def _detect_cnpj(self, raw_text: str) -> Optional[str]:
        match = CNPJ_PATTERN.search(raw_text)
        if match:
            raw = match.group(0)
            digits = re.sub(r'\D', '', raw)
            if len(digits) == 14:
                return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return None

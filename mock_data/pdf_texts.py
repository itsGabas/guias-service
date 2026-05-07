# Textos que simulam o conteúdo extraído de PDFs reais.
# Usados nos testes para validar o PDFService sem precisar de arquivos .pdf

PDF_HOLERITE = """
HOLERITE DE PAGAMENTO
Empresa: Padaria São João Ltda
CNPJ: 12.345.678/0001-90
Funcionário: João da Silva
Matrícula: 00123
Competência: Janeiro/2026
Salário Bruto: R$ 2.500,00
INSS: R$ 275,00
IRRF: R$ 0,00
Salário Líquido: R$ 2.225,00
"""

PDF_EXTRATO = """
EXTRATO DE MOVIMENTAÇÃO MENSAL
Banco: Banco do Brasil S.A.
Agência: 1234-5  Conta: 00001-2
Titular: Padaria São João Ltda
CNPJ: 12.345.678/0001-90
Referente ao mês: 01/2026
Saldo Inicial: R$ 10.000,00
Total Créditos: R$ 35.000,00
Total Débitos: R$ 28.000,00
Saldo Final: R$ 17.000,00
"""

PDF_DARF = """
DOCUMENTO DE ARRECADAÇÃO DE RECEITAS FEDERAIS - DARF
Contribuinte: Tech Solutions ME
CNPJ: 98.765.432/0001-11
Código do Tributo: 2089 - SIMPLES NACIONAL
Período de Apuração: 01/2026
Valor Principal: R$ 1.250,00
Valor Total: R$ 1.250,00
Data de Vencimento: 20/02/2026
"""

PDF_SEM_DADOS = """
DOCUMENTO INTERNO
Arquivo gerado pelo sistema.
Sem informações de empresa ou competência.
"""

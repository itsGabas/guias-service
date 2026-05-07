from app.models.client import Client

MOCK_CLIENTS = [
    Client(
        id="cli-001",
        company_name="Padaria São João Ltda",
        cnpj="12.345.678/0001-90",
        inscricao_estadual="062.307.904/0001",   # formato MG
        email="financeiro@padariasaojoao.com.br",
        responsible="Ana Paula",
        department="RH",
        phone="(35) 99801-1234",
    ),
    Client(
        id="cli-002",
        company_name="Tech Solutions ME",
        cnpj="98.765.432/0001-11",
        inscricao_estadual="110.042.490.114",    # formato SP
        email="contato@techsolutions.com.br",
        responsible="Carlos Eduardo",
        department="CONTABIL",
        phone="(35) 98800-5678",
    ),
    Client(
        id="cli-003",
        company_name="Distribuidora Norte SA",
        cnpj="55.444.333/0001-22",
        inscricao_estadual=None,                 # sem IE cadastrada
        email="juridico@distribuidoranorte.com.br",
        responsible="Fernanda Lima",
        department="FISCAL",
    ),
]

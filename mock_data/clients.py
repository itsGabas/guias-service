from app.models.client import Client

MOCK_CLIENTS = [
    Client(
        id="501",
        company_name="GGM / AG LOG LTDA",
        cnpj="47958477000148",
        email="gabriel@triarcontabilidade.com.br",
        responsible="Yasmin Teodoro",
        department="FISCAL",
    ),
    Client(
        id="502",
        company_name="Tech Solutions ME",
        cnpj="98.765.432/0001-11",
        email="contato@techsolutions.com.br",
        responsible="Carlos Eduardo",
        department="CONTABIL",
    ),
    Client(
        id="503",
        company_name="Distribuidora Norte SA",
        cnpj="55.444.333/0001-22",
        email="juridico@distribuidoranorte.com.br",
        responsible="Fernanda Lima",
        department="FISCAL",
    ),
]

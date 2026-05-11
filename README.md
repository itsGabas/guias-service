# Guias Service — API REST

Microsserviço Python para criação de templates, identificação automática de PDFs e envio de guias por departamento.

## Stack
- **Python 3.11+**
- **FastAPI** + **Uvicorn**
- **PyMuPDF** — leitura de PDF
- **openpyxl** — importação de planilha de empresas

## Instalação

```bash
pip install fastapi uvicorn pymupdf openpyxl python-multipart
```

## Configuração

Copie `.env.example` para `.env` e preencha:

```env
GMAIL_REMETENTE=seuemail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

## Rodar

```bash
python -m uvicorn app.main:app --reload
```

Documentação interativa: **http://localhost:8000/docs**

---

## Endpoints

### 🏢 Empresas `/clients`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/clients/` | Listar empresas (filtro por `?q=`) |
| GET | `/clients/{id}` | Buscar empresa |
| POST | `/clients/sync` | Importar planilha .xlsx (INSERT/UPDATE/DELETE) |
| GET | `/clients/{id}/emails` | Listar e-mails da empresa |
| POST | `/clients/{id}/emails` | Adicionar e-mail com departamentos |
| DELETE | `/clients/{id}/emails/{email}` | Remover e-mail |
| GET | `/clients/{id}/emails/department/{dept}` | E-mails de um departamento específico |

### 📋 Templates `/templates`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/templates/` | Listar templates |
| POST | `/templates/` | Criar template com palavras-chave |
| DELETE | `/templates/{id}` | Remover template |
| POST | `/templates/{id}/validate` | Validar template com PDF modelo |
| POST | `/templates/match/pdf` | Identificar template + empresa de um PDF |

### 📤 Tarefas & PDFs `/tasks`
| Método | Rota | Descrição |
|---|---|---|
| POST | `/tasks/upload` | Upload de PDF → retorna dados extraídos + validação |
| POST | `/tasks/send` | Disparar envio dos PDFs analisados |

### 📜 Histórico `/emails`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/emails/logs` | Histórico completo (filtros: client_id, status, department) |
| GET | `/emails/logs/{id}` | Log específico |
| GET | `/emails/logs/{id}/download` | Download do PDF do histórico |
| GET | `/emails/logs/client/{id}` | Histórico de uma empresa |

### Status
| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Health check |
| GET | `/stats` | Totais do sistema |

---

## Fluxo de integração (Node.js → Python)

```
1. POST /clients/sync          → importa planilha de empresas
2. POST /clients/{id}/emails   → cadastra e-mails por departamento
3. POST /templates/            → cria template com palavras-chave
4. POST /tasks/upload          → analisa PDF (retorna can_send, block_reasons)
5. POST /tasks/send            → dispara envio
6. GET  /emails/logs           → consulta histórico
7. GET  /emails/logs/{id}/download → baixa PDF do histórico
```

## Estrutura

```
guias_service/
├── app/
│   ├── main.py                  ← inicialização FastAPI
│   ├── models/
│   │   ├── client.py            ← Client + ClientEmail
│   │   ├── task_template.py     ← TaskTemplate (keywords)
│   │   ├── email_log.py         ← EmailLog (histórico)
│   │   └── enums.py             ← Department, TaskStatus, etc.
│   ├── repositories/
│   │   └── mock_repository.py   ← banco em memória (→ Supabase)
│   ├── routers/
│   │   ├── clients.py
│   │   ├── templates.py
│   │   ├── tasks.py
│   │   └── emails.py
│   └── services/
│       ├── pdf_service.py       ← leitura + identificação de PDF
│       └── xlsx_service.py      ← importação de planilha
├── historico/
│   └── pdfs/                    ← cópias dos PDFs enviados
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Próximo passo — Supabase

Quando integrar o banco, criar `SupabaseRepository` com a mesma interface
do `MockRepository` e trocar a instância em `app/main.py`. Nenhum router precisa mudar.

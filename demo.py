"""
DEMO INTERATIVO — Sistema de Guias
Execute: python demo.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.models.enums import DocumentType, Department
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService
from app.services.task_service import TaskService
from app.services.email_service import EmailService
from app.models.client import Client
from mock_data.clients import MOCK_CLIENTS


# ── HELPERS VISUAIS ───────────────────────────────────────────────────

def linha(char="─", n=58):
    print(char * n)

def titulo(texto):
    linha("═")
    print(f"  {texto}")
    linha("═")

def secao(texto):
    print(f"\n{'─'*58}")
    print(f"  {texto}")
    linha()

def input_opcao(prompt, opcoes: list[str]) -> str:
    """Exibe opções numeradas e retorna a escolha."""
    for i, op in enumerate(opcoes, 1):
        print(f"  [{i}] {op}")
    while True:
        escolha = input(f"\n  → ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return opcoes[int(escolha) - 1]
        print("  ⚠ Opção inválida. Tente novamente.")

def input_texto(prompt, obrigatorio=True) -> str:
    while True:
        val = input(f"  {prompt}: ").strip()
        if val or not obrigatorio:
            return val
        print("  ⚠ Campo obrigatório.")

def pausar():
    input("\n  [ENTER para continuar]")


# ── SETUP ─────────────────────────────────────────────────────────────

def setup():
    repo = MockRepository()
    for c in MOCK_CLIENTS:
        repo.save_client(c)
    pdf_svc  = PDFService()
    task_svc = TaskService(repo, pdf_svc)
    email_svc = EmailService(repo)
    return repo, task_svc, email_svc, pdf_svc


# ── ETAPAS DO FLUXO ───────────────────────────────────────────────────

def escolher_cliente(repo) -> str:
    secao("PASSO 1 — Escolha o cliente")
    clientes = repo.list_clients()
    nomes = [f"{c.company_name}  ({c.cnpj})  → {c.email}" for c in clientes]
    escolha = input_opcao("Cliente:", nomes)
    idx = nomes.index(escolha)
    cliente = clientes[idx]
    print(f"\n  ✅ Cliente selecionado: {cliente.company_name}")
    return cliente.id


def criar_tarefa(task_svc, client_id: str):
    secao("PASSO 2 — Criar a tarefa")

    titulo_task = input_texto("Título da tarefa (ex: Envio Holerites Janeiro)")
    competencia = input_texto("Competência (ex: Janeiro/2026)")

    print("\n  Departamento responsável:")
    depto_nome = input_opcao("", [d.value for d in Department])
    depto = Department(depto_nome)

    criado_por = input_texto("Seu nome (quem está criando)")

    task = task_svc.create_task(
        title=titulo_task,
        client_id=client_id,
        competence=competencia,
        department=depto,
        created_by=criado_por,
    )
    print(f"\n  ✅ Tarefa criada! ID: {task.id}")
    return task


def adicionar_pdfs(task_svc, task):
    secao("PASSO 3 — Adicionar PDFs à tarefa")

    documentos_adicionados = []

    while True:
        print(f"\n  Documentos na tarefa: {task.document_count()}")
        print("  O que deseja fazer?")
        acao = input_opcao("", [
            "Adicionar um PDF",
            "Continuar (já terminei de adicionar)",
        ])

        if acao.startswith("Continuar"):
            if task.document_count() == 0:
                print("  ⚠ Adicione pelo menos 1 PDF antes de continuar.")
                continue
            break

        # ── Leitura do arquivo ──
        caminho = input_texto("Caminho completo do PDF (ex: C:\\Users\\voce\\holerite.pdf)").strip('"').strip("'")

        if not os.path.exists(caminho):
            print(f"  ❌ Arquivo não encontrado: {caminho}")
            continue

        filename = os.path.basename(caminho)
        size_kb  = os.path.getsize(caminho) / 1024

        print(f"\n  📄 Arquivo: {filename}  ({size_kb:.1f} KB)")
        print("  🔍 Lendo e analisando o PDF...\n")

        # ── Extração automática ──
        pdf_svc = PDFService()
        extraction = pdf_svc.extract_from_file(caminho)

        linha()
        print("  RESULTADO DA LEITURA AUTOMÁTICA")
        linha()
        print(f"  Confiança   : {extraction.confidence:.0%}")
        print(f"  Tipo         : {extraction.suggested_type.value if extraction.suggested_type else '❓ Não identificado'}")
        print(f"  Competência  : {extraction.suggested_competence or '❓ Não encontrada'}")
        print(f"  CNPJ no PDF  : {extraction.suggested_company_cnpj or '❓ Não encontrado'}")
        if extraction.warnings:
            for w in extraction.warnings:
                print(f"  ⚠  {w}")
        linha()

        # ── Confirmação / correção pelo usuário ──
        print("\n  Confirme ou corrija os dados detectados:\n")

        # Tipo
        tipos = [d.value for d in DocumentType]
        sugerido = extraction.suggested_type.value if extraction.suggested_type else None
        if sugerido and sugerido in tipos:
            idx_sug = tipos.index(sugerido)
            tipos.insert(0, tipos.pop(idx_sug))   # coloca o sugerido primeiro
            tipos[0] = f"{tipos[0]}  ← sugerido"

        print("  Tipo do documento:")
        tipo_escolhido = input_opcao("", tipos)
        tipo_escolhido = tipo_escolhido.replace("  ← sugerido", "")
        doc_type = DocumentType(tipo_escolhido)

        # Competência
        comp_sug = extraction.suggested_competence or task.competence
        comp_input = input(f"  Competência [{comp_sug}]: ").strip()
        competencia_final = comp_input if comp_input else comp_sug

        # ── Adiciona o documento ──
        doc = task_svc.add_document_from_text(
            task_id=task.id,
            filename=filename,
            file_size_kb=size_kb,
            raw_text=extraction.raw_text,
            file_path=caminho,
            manual_type=doc_type,
            manual_competence=competencia_final,
        )

        # ── Confirmação automática (usuário já revisou acima) ──
        task_svc.confirm_document(task.id, doc.id)
        print(f"\n  ✅ Documento adicionado e confirmado: {doc}")
        documentos_adicionados.append(doc)

        task = task_svc.get_task(task.id)

    return task_svc.get_task(task.id)


def revisar_e_enviar(task_svc, email_svc, repo, task):
    secao("PASSO 4 — Revisão final e envio")

    cliente = repo.get_client(task.client_id)
    linha()
    print("  RESUMO DA TAREFA")
    linha()
    print(f"  Título      : {task.title}")
    print(f"  Cliente     : {cliente.company_name}")
    print(f"  E-mail      : {cliente.email}")
    print(f"  Competência : {task.competence}")
    print(f"  Departamento: {task.department.value}")
    print(f"  Documentos  : {task.document_count()}")
    for doc in task.documents:
        status = "✓" if doc.confirmed else "⚠"
        print(f"    {status} {doc.document_type.value} — {doc.filename} ({doc.file_size_kb:.1f} KB)")
    print(f"  Tamanho total: {task.total_size_kb():.1f} KB")
    linha()

    pode, motivo = task.can_send()
    if not pode:
        print(f"\n  ❌ Envio bloqueado: {motivo}")
        return

    print("\n  Tudo pronto. Deseja enviar agora?")
    confirmacao = input_opcao("", ["Sim, enviar agora", "Cancelar"])

    if confirmacao.startswith("Cancelar"):
        print("  ↩ Envio cancelado.")
        return

    enviado_por = input_texto("Seu nome (para o log de envio)")

    print("\n  🚀 Disparando envio...\n")
    log = email_svc.send_task(task, sent_by=enviado_por)

    secao("LOG DO ENVIO")
    for k, v in log.summary().items():
        print(f"  {k:<25}: {v}")

    task_final = task_svc.get_task(task.id)
    print(f"\n  Status final da tarefa: {task_final.status.value}")
    if task_final.sent_at:
        print(f"  Enviada em: {task_final.sent_at.strftime('%d/%m/%Y às %H:%M:%S')}")


# ── MAIN ──────────────────────────────────────────────────────────────

def main():
    titulo("SISTEMA DE GUIAS — DEMO INTERATIVO")
    print("  Este script simula o fluxo completo:")
    print("  Criar tarefa → Subir PDFs → Detectar → Confirmar → Enviar\n")
    print("  (O envio é SIMULADO — nenhum e-mail real será disparado)\n")
    pausar()

    repo, task_svc, email_svc, _ = setup()

    client_id = escolher_cliente(repo)
    task      = criar_tarefa(task_svc, client_id)
    task      = adicionar_pdfs(task_svc, task)
    revisar_e_enviar(task_svc, email_svc, repo, task)

    titulo("FIM DA DEMO")
    print("  Quando o Supabase e o e-mail real estiverem configurados,")
    print("  este fluxo funcionará exatamente igual — só muda o repositório")
    print("  e a flag USE_REAL_SMTP no email_service.py.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Demo encerrada pelo usuário.")

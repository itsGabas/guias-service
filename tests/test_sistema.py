"""
SUITE DE TESTES — Sistema de Tarefas e Envio de Guias
Execute com: python -m pytest tests/test_sistema.py -v
Ou diretamente: python tests/test_sistema.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.enums import DocumentType, Department, TaskStatus
from app.models.email_log import EmailStatus
from app.repositories.mock_repository import MockRepository
from app.services.pdf_service import PDFService
from app.services.task_service import TaskService
from app.services.email_service import EmailService
from mock_data.clients import MOCK_CLIENTS
from mock_data.pdf_texts import PDF_HOLERITE, PDF_EXTRATO, PDF_DARF, PDF_SEM_DADOS


# ── SETUP ─────────────────────────────────────────────────────────────

def build_services():
    repo = MockRepository()
    for client in MOCK_CLIENTS:
        repo.save_client(client)
    pdf_svc = PDFService()
    task_svc = TaskService(repo, pdf_svc)
    email_svc = EmailService(repo)
    return repo, task_svc, email_svc, pdf_svc


# ══════════════════════════════════════════════════════════════════════
# BLOCO 1 — PDF SERVICE
# ══════════════════════════════════════════════════════════════════════

def test_pdf_detecta_holerite():
    print("\n[TESTE 1.1] PDF detecta tipo HOLERITE")
    svc = PDFService()
    result = svc.extract_from_text(PDF_HOLERITE)
    assert result.suggested_type == DocumentType.HOLERITE, f"Esperado HOLERITE, obtido: {result.suggested_type}"
    assert "Janeiro" in result.suggested_competence, f"Competência errada: {result.suggested_competence}"
    assert result.suggested_company_cnpj is not None, "CNPJ não encontrado"
    print(f"  ✅ Tipo: {result.suggested_type.value} | Competência: {result.suggested_competence} | CNPJ: {result.suggested_company_cnpj}")


def test_pdf_detecta_extrato():
    print("\n[TESTE 1.2] PDF detecta tipo EXTRATO_MENSAL com competência numérica")
    svc = PDFService()
    result = svc.extract_from_text(PDF_EXTRATO)
    assert result.suggested_type == DocumentType.EXTRATO_MENSAL
    assert result.suggested_competence is not None
    print(f"  ✅ Tipo: {result.suggested_type.value} | Competência: {result.suggested_competence}")


def test_pdf_detecta_darf():
    print("\n[TESTE 1.3] PDF detecta tipo DARF")
    svc = PDFService()
    result = svc.extract_from_text(PDF_DARF)
    assert result.suggested_type == DocumentType.DARF
    print(f"  ✅ Tipo: {result.suggested_type.value} | Confiança: {result.confidence:.0%}")


def test_pdf_sem_dados_retorna_warnings():
    print("\n[TESTE 1.4] PDF sem dados retorna baixa confiança e warnings")
    svc = PDFService()
    result = svc.extract_from_text(PDF_SEM_DADOS)
    assert result.confidence < 0.5, f"Confiança deveria ser baixa: {result.confidence}"
    assert len(result.warnings) > 0
    print(f"  ✅ Confiança: {result.confidence:.0%} | Warnings: {result.warnings}")


# ══════════════════════════════════════════════════════════════════════
# BLOCO 2 — TASK SERVICE
# ══════════════════════════════════════════════════════════════════════

def test_criar_tarefa():
    print("\n[TESTE 2.1] Criação de tarefa vinculada a cliente válido")
    repo, task_svc, _, _ = build_services()
    task = task_svc.create_task(
        title="Envio de Holerites e Extrato",
        client_id="cli-001",
        competence="Janeiro/2026",
        department=Department.RH,
        created_by="Ana Paula",
    )
    assert task.id is not None
    assert task.status == TaskStatus.PENDENTE
    assert task.document_count() == 0
    print(f"  ✅ {task}")


def test_criar_tarefa_cliente_inexistente():
    print("\n[TESTE 2.2] Criação de tarefa com cliente inválido deve lançar erro")
    repo, task_svc, _, _ = build_services()
    try:
        task_svc.create_task("Teste", "cli-INVALIDO", "Jan/2026", Department.RH, "Teste")
        assert False, "Deveria ter lançado ValueError"
    except ValueError as e:
        print(f"  ✅ Erro esperado: {e}")


def test_adicionar_documentos_multiplos():
    print("\n[TESTE 2.3] Adicionar múltiplos documentos (Holerite + Extrato) em uma tarefa")
    repo, task_svc, _, _ = build_services()
    task = task_svc.create_task("Envios RH Jan", "cli-001", "Janeiro/2026", Department.RH, "Ana Paula")

    doc1 = task_svc.add_document_from_text(
        task_id=task.id,
        filename="holerite_joao_jan2026.pdf",
        file_size_kb=45.2,
        raw_text=PDF_HOLERITE,
    )
    doc2 = task_svc.add_document_from_text(
        task_id=task.id,
        filename="extrato_jan2026.pdf",
        file_size_kb=82.7,
        raw_text=PDF_EXTRATO,
    )

    task_atualizada = task_svc.get_task(task.id)
    assert task_atualizada.document_count() == 2
    assert doc1.document_type == DocumentType.HOLERITE
    assert doc2.document_type == DocumentType.EXTRATO_MENSAL
    print(f"  ✅ Documentos: {task_atualizada.document_count()} | Size total: {task_atualizada.total_size_kb():.1f} KB")


def test_fluxo_hibrido_manual_override():
    print("\n[TESTE 2.4] Fluxo híbrido: usuário corrige tipo manualmente")
    repo, task_svc, _, _ = build_services()
    task = task_svc.create_task("Envio Fiscal", "cli-002", "Janeiro/2026", Department.FISCAL, "Carlos")

    # PDF sem dados claros, usuário define manualmente
    doc = task_svc.add_document_from_text(
        task_id=task.id,
        filename="guia_fgts_jan2026.pdf",
        file_size_kb=30.0,
        raw_text=PDF_SEM_DADOS,
        manual_type=DocumentType.GUIA_FGTS,
        manual_competence="Janeiro/2026",
    )
    assert doc.document_type == DocumentType.GUIA_FGTS
    assert doc.competence == "Janeiro/2026"
    print(f"  ✅ Tipo (manual): {doc.document_type.value} | Competência: {doc.competence}")


def test_confirmacao_documentos():
    print("\n[TESTE 2.5] Confirmação de documentos pelo usuário")
    repo, task_svc, _, _ = build_services()
    task = task_svc.create_task("Envio RH", "cli-001", "Janeiro/2026", Department.RH, "Ana")
    doc = task_svc.add_document_from_text(task.id, "holerite.pdf", 40.0, PDF_HOLERITE)

    assert not task_svc.get_task(task.id).all_documents_confirmed()
    task_svc.confirm_document(task.id, doc.id)
    assert task_svc.get_task(task.id).all_documents_confirmed()
    print(f"  ✅ Documento confirmado com sucesso")


def test_remover_documento():
    print("\n[TESTE 2.6] Remoção de documento da tarefa")
    repo, task_svc, _, _ = build_services()
    task = task_svc.create_task("Envio", "cli-001", "Jan/2026", Department.RH, "Ana")
    doc = task_svc.add_document_from_text(task.id, "holerite.pdf", 40.0, PDF_HOLERITE)
    assert task_svc.get_task(task.id).document_count() == 1
    task_svc.remove_document(task.id, doc.id)
    assert task_svc.get_task(task.id).document_count() == 0
    print(f"  ✅ Documento removido. Total restante: 0")


# ══════════════════════════════════════════════════════════════════════
# BLOCO 3 — EMAIL SERVICE
# ══════════════════════════════════════════════════════════════════════

def _criar_tarefa_pronta(task_svc, client_id="cli-001"):
    """Helper: cria tarefa com 2 docs confirmados, pronta para envio."""
    task = task_svc.create_task("Envio Guias", client_id, "Janeiro/2026", Department.RH, "Ana Paula")
    d1 = task_svc.add_document_from_text(task.id, "holerite.pdf", 45.0, PDF_HOLERITE)
    d2 = task_svc.add_document_from_text(task.id, "extrato.pdf", 80.0, PDF_EXTRATO)
    task_svc.confirm_document(task.id, d1.id)
    task_svc.confirm_document(task.id, d2.id)
    return task_svc.get_task(task.id)


def test_envio_simulado_sucesso():
    print("\n[TESTE 3.1] Envio simulado com sucesso (mock SMTP)")
    repo, task_svc, email_svc, _ = build_services()
    task = _criar_tarefa_pronta(task_svc)

    log = email_svc.send_task(task, sent_by="Ana Paula")

    assert log.status == EmailStatus.SIMULADO
    assert log.task_id == task.id
    assert len(log.documents_sent) == 2

    task_atualizada = task_svc.get_task(task.id)
    assert task_atualizada.status == TaskStatus.ENVIADA
    assert task_atualizada.sent_at is not None
    print(f"  ✅ Enviado com sucesso | Status task: {task_atualizada.status.value}")


def test_envio_bloqueado_sem_documentos():
    print("\n[TESTE 3.2] Envio bloqueado: tarefa sem documentos")
    repo, task_svc, email_svc, _ = build_services()
    task = task_svc.create_task("Vazia", "cli-001", "Jan/2026", Department.RH, "Ana")
    task_obj = task_svc.get_task(task.id)
    try:
        email_svc.send_task(task_obj, sent_by="Ana")
        assert False, "Deveria ter bloqueado"
    except ValueError as e:
        print(f"  ✅ Bloqueado corretamente: {e}")


def test_envio_bloqueado_sem_confirmacao():
    print("\n[TESTE 3.3] Envio bloqueado: documentos não confirmados")
    repo, task_svc, email_svc, _ = build_services()
    task = task_svc.create_task("Sem confirm", "cli-001", "Jan/2026", Department.RH, "Ana")
    task_svc.add_document_from_text(task.id, "holerite.pdf", 40.0, PDF_HOLERITE)
    task_obj = task_svc.get_task(task.id)
    try:
        email_svc.send_task(task_obj, sent_by="Ana")
        assert False, "Deveria ter bloqueado"
    except ValueError as e:
        print(f"  ✅ Bloqueado corretamente: {e}")


def test_envio_bloqueado_tarefa_ja_enviada():
    print("\n[TESTE 3.4] Envio bloqueado: tarefa já foi enviada")
    repo, task_svc, email_svc, _ = build_services()
    task = _criar_tarefa_pronta(task_svc)
    email_svc.send_task(task, sent_by="Ana")          # 1º envio
    task_atualizada = task_svc.get_task(task.id)
    try:
        email_svc.send_task(task_atualizada, sent_by="Ana")  # 2º deve bloquear
        assert False
    except ValueError as e:
        print(f"  ✅ Bloqueado corretamente: {e}")


# ══════════════════════════════════════════════════════════════════════
# BLOCO 4 — LOGS E REPOSITÓRIO
# ══════════════════════════════════════════════════════════════════════

def test_log_registrado_no_repositorio():
    print("\n[TESTE 4.1] Log de envio registrado no repositório")
    repo, task_svc, email_svc, _ = build_services()
    task = _criar_tarefa_pronta(task_svc)
    log = email_svc.send_task(task, sent_by="Ana Paula")

    logs = repo.get_logs_by_task(task.id)
    assert len(logs) == 1
    assert logs[0].id == log.id
    print(f"  ✅ Log salvo | ID: {log.id} | Status: {log.status.value}")


def test_stats_repositorio():
    print("\n[TESTE 4.2] Stats do repositório após múltiplas operações")
    repo, task_svc, email_svc, _ = build_services()

    # Cria 2 tarefas, envia 1
    t1 = _criar_tarefa_pronta(task_svc, "cli-001")
    t2 = _criar_tarefa_pronta(task_svc, "cli-002")
    email_svc.send_task(t1, "Ana")

    stats = repo.stats()
    assert stats["total_clients"] == 3
    assert stats["total_tasks"] == 2
    assert stats["tasks_enviadas"] == 1
    assert stats["tasks_pendentes"] == 1
    print(f"  ✅ Stats: {stats}")


# ══════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    # PDF Service
    test_pdf_detecta_holerite,
    test_pdf_detecta_extrato,
    test_pdf_detecta_darf,
    test_pdf_sem_dados_retorna_warnings,
    # Task Service
    test_criar_tarefa,
    test_criar_tarefa_cliente_inexistente,
    test_adicionar_documentos_multiplos,
    test_fluxo_hibrido_manual_override,
    test_confirmacao_documentos,
    test_remover_documento,
    # Email Service
    test_envio_simulado_sucesso,
    test_envio_bloqueado_sem_documentos,
    test_envio_bloqueado_sem_confirmacao,
    test_envio_bloqueado_tarefa_ja_enviada,
    # Repositório
    test_log_registrado_no_repositorio,
    test_stats_repositorio,
]

if __name__ == "__main__":
    passed, failed = 0, []
    print("=" * 60)
    print("  SUITE DE TESTES — SISTEMA DE GUIAS")
    print("=" * 60)

    for test_fn in ALL_TESTS:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed.append((test_fn.__name__, str(e)))
            print(f"  ❌ FALHOU: {test_fn.__name__} → {e}")

    print("\n" + "=" * 60)
    print(f"  RESULTADO: {passed}/{len(ALL_TESTS)} testes passaram")
    if failed:
        print(f"\n  FALHOS:")
        for name, err in failed:
            print(f"    - {name}: {err}")
    else:
        print("  ✅ Todos os testes passaram!")
    print("=" * 60)

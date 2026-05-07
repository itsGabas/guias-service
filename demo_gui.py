"""
DEMO COM INTERFACE — Sistema de Guias
Seleção de PDF por janela + envio real via Gmail SMTP

Execute: python demo_gui.py
"""
import os
import sys
import smtplib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.services.pdf_service import PDFService
from app.models.enums import DocumentType
from app.repositories.mock_repository import MockRepository
from app.models.client import Client

# ══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO — preencha aqui antes de rodar
# ══════════════════════════════════════════════════════════════════════

GMAIL_REMETENTE = "xxxx"          # seu Gmail
GMAIL_APP_PASSWORD = "senha_api"      # App Password de 16 dígitos
EMAIL_DESTINATARIO = "xxxx"

# ══════════════════════════════════════════════════════════════════════


class DocumentoDetectado:
    """Agrupa o PDF físico com os dados extraídos e confirmados."""
    def __init__(self, caminho: str, extracao, tipo_final: DocumentType, competencia_final: str):
        self.caminho = caminho
        self.filename = os.path.basename(caminho)
        self.size_kb = os.path.getsize(caminho) / 1024
        self.extracao = extracao
        self.tipo = tipo_final
        self.competencia = competencia_final

    def __repr__(self):
        return f"<Doc {self.tipo.value} | {self.competencia} | {self.filename}>"


class DemoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistema de Guias — Demo")
        self.root.geometry("720x640")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.pdf_svc = PDFService()
        self.documentos: list[DocumentoDetectado] = []
        self.empresa_detectada = None

        self._build_ui()

    # ── INTERFACE ─────────────────────────────────────────────────────

    def _build_ui(self):
        FONTE_TITLE = ("Segoe UI", 14, "bold")
        FONTE_LABEL = ("Segoe UI", 10)
        FONTE_MONO  = ("Consolas", 9)
        COR_BG      = "#1e1e2e"
        COR_PANEL   = "#2a2a3e"
        COR_ACCENT  = "#7c6af7"
        COR_TEXT    = "#cdd6f4"
        COR_SUB     = "#a6adc8"
        COR_OK      = "#a6e3a1"
        COR_WARN    = "#f9e2af"
        COR_ERR     = "#f38ba8"

        self._cores = {
            "bg": COR_BG, "panel": COR_PANEL, "accent": COR_ACCENT,
            "text": COR_TEXT, "sub": COR_SUB, "ok": COR_OK,
            "warn": COR_WARN, "err": COR_ERR,
        }

        # ── Título ──
        tk.Label(self.root, text="📄 Sistema de Guias — Teste de Envio",
                 font=FONTE_TITLE, bg=COR_BG, fg=COR_TEXT).pack(pady=(18, 2))
        tk.Label(self.root, text="Selecione os PDFs, confirme os dados e dispare o e-mail",
                 font=("Segoe UI", 9), bg=COR_BG, fg=COR_SUB).pack(pady=(0, 14))

        # ── Botão selecionar PDF ──
        tk.Button(
            self.root, text="+ Selecionar PDF(s)",
            font=("Segoe UI", 10, "bold"), bg=COR_ACCENT, fg="white",
            relief="flat", padx=18, pady=8, cursor="hand2",
            command=self._selecionar_pdfs
        ).pack()

        # ── Lista de documentos ──
        frame_lista = tk.Frame(self.root, bg=COR_PANEL, bd=0)
        frame_lista.pack(fill="x", padx=24, pady=(14, 0))

        tk.Label(frame_lista, text="Documentos adicionados:",
                 font=("Segoe UI", 9, "bold"), bg=COR_PANEL, fg=COR_SUB).pack(anchor="w", padx=10, pady=(8, 2))

        self.lista_box = tk.Listbox(
            frame_lista, height=5, font=FONTE_MONO,
            bg="#13131f", fg=COR_TEXT, selectbackground=COR_ACCENT,
            relief="flat", bd=0, highlightthickness=0,
        )
        self.lista_box.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(frame_lista, text="🗑 Remover selecionado",
                  font=("Segoe UI", 8), bg="#313244", fg=COR_SUB,
                  relief="flat", cursor="hand2", pady=4,
                  command=self._remover_documento).pack(anchor="e", padx=10, pady=(0, 8))

        # ── Empresa detectada ──
        frame_emp = tk.Frame(self.root, bg=COR_PANEL)
        frame_emp.pack(fill="x", padx=24, pady=(10, 0))

        tk.Label(frame_emp, text="Empresa detectada (CNPJ):",
                 font=("Segoe UI", 9, "bold"), bg=COR_PANEL, fg=COR_SUB).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))

        self.var_empresa = tk.StringVar(value="—")
        tk.Label(frame_emp, textvariable=self.var_empresa,
                 font=("Segoe UI", 10), bg=COR_PANEL, fg=COR_OK).grid(row=0, column=1, sticky="w", padx=6, pady=(8, 2))

        tk.Label(frame_emp, text="Competência:",
                 font=("Segoe UI", 9, "bold"), bg=COR_PANEL, fg=COR_SUB).grid(row=1, column=0, sticky="w", padx=10, pady=2)

        self.var_competencia = tk.StringVar()
        tk.Entry(frame_emp, textvariable=self.var_competencia,
                 font=FONTE_LABEL, bg="#13131f", fg=COR_TEXT,
                 insertbackground=COR_TEXT, relief="flat", width=20).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        # ── Log visual ──
        frame_log = tk.Frame(self.root, bg=COR_PANEL)
        frame_log.pack(fill="both", expand=True, padx=24, pady=(14, 0))

        tk.Label(frame_log, text="Log de análise:",
                 font=("Segoe UI", 9, "bold"), bg=COR_PANEL, fg=COR_SUB).pack(anchor="w", padx=10, pady=(8, 2))

        self.log_text = tk.Text(
            frame_log, height=10, font=FONTE_MONO,
            bg="#13131f", fg=COR_TEXT, relief="flat",
            bd=0, highlightthickness=0, state="disabled",
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Tags de cor no log
        self.log_text.tag_config("ok",   foreground=COR_OK)
        self.log_text.tag_config("warn", foreground=COR_WARN)
        self.log_text.tag_config("err",  foreground=COR_ERR)
        self.log_text.tag_config("info", foreground="#89b4fa")
        self.log_text.tag_config("bold", font=("Consolas", 9, "bold"))

        # ── Botão enviar ──
        self.btn_enviar = tk.Button(
            self.root, text="🚀 Enviar E-mail de Teste",
            font=("Segoe UI", 11, "bold"), bg="#40a060", fg="white",
            relief="flat", padx=20, pady=10, cursor="hand2",
            command=self._confirmar_e_enviar, state="disabled"
        )
        self.btn_enviar.pack(pady=14)

    # ── AÇÕES ─────────────────────────────────────────────────────────

    def _selecionar_pdfs(self):
        caminhos = filedialog.askopenfilenames(
            title="Selecione os PDFs",
            filetypes=[("Arquivos PDF", "*.pdf")],
        )
        if not caminhos:
            return
        for caminho in caminhos:
            self._processar_pdf(caminho)
        self._atualizar_botao_enviar()

    def _processar_pdf(self, caminho: str):
        filename = os.path.basename(caminho)
        self._log(f"\n{'─'*48}", "info")
        self._log(f"📄 Processando: {filename}", "bold")
        self._log(f"   Tamanho: {os.path.getsize(caminho)/1024:.1f} KB")

        extracao = self.pdf_svc.extract_from_file(caminho)

        self._log(f"   Confiança da leitura: {extracao.confidence:.0%}",
                  "ok" if extracao.confidence >= 0.6 else "warn")
        self._log(f"   Tipo detectado    : {extracao.suggested_type.value if extracao.suggested_type else '❓ Não identificado'}",
                  "ok" if extracao.suggested_type else "warn")
        self._log(f"   Competência       : {extracao.suggested_competence or '❓ Não encontrada'}",
                  "ok" if extracao.suggested_competence else "warn")
        self._log(f"   CNPJ no PDF       : {extracao.suggested_company_cnpj or '❓ Não encontrado'}",
                  "ok" if extracao.suggested_company_cnpj else "warn")

        for w in extracao.warnings:
            self._log(f"   ⚠ {w}", "warn")

        # Abre janela de confirmação/correção
        tipo_final, comp_final = self._janela_confirmacao(filename, extracao)
        if tipo_final is None:
            self._log("   ↩ Documento ignorado pelo usuário.", "warn")
            return

        doc = DocumentoDetectado(caminho, extracao, tipo_final, comp_final)
        self.documentos.append(doc)
        self.lista_box.insert("end", f"  ✓  {doc.tipo.value:<22} {doc.filename}")
        self._log(f"   ✅ Adicionado: {doc.tipo.value} — {comp_final}", "ok")

        # Atualiza empresa detectada
        if extracao.suggested_company_cnpj and self.empresa_detectada is None:
            self.empresa_detectada = extracao.suggested_company_cnpj
            self.var_empresa.set(extracao.suggested_company_cnpj)

        # Preenche competência se ainda vazia
        if extracao.suggested_competence and not self.var_competencia.get():
            self.var_competencia.set(extracao.suggested_competence)

    def _janela_confirmacao(self, filename: str, extracao) -> tuple:
        """Abre popup para o usuário confirmar/corrigir tipo e competência."""
        popup = tk.Toplevel(self.root)
        popup.title("Confirmar dados do PDF")
        popup.geometry("460x320")
        popup.configure(bg="#1e1e2e")
        popup.grab_set()

        COR_BG    = "#1e1e2e"
        COR_TEXT  = "#cdd6f4"
        COR_PANEL = "#2a2a3e"
        COR_ACCENT= "#7c6af7"

        resultado = {"tipo": None, "competencia": None}

        tk.Label(popup, text=f"Confirme os dados detectados",
                 font=("Segoe UI", 11, "bold"), bg=COR_BG, fg=COR_TEXT).pack(pady=(16, 2))
        tk.Label(popup, text=filename,
                 font=("Consolas", 9), bg=COR_BG, fg="#a6adc8").pack(pady=(0, 12))

        frame = tk.Frame(popup, bg=COR_PANEL)
        frame.pack(fill="x", padx=20)

        # Tipo
        tk.Label(frame, text="Tipo do documento:", font=("Segoe UI", 9, "bold"),
                 bg=COR_PANEL, fg="#a6adc8").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))

        tipos = [d.value for d in DocumentType]
        var_tipo = tk.StringVar(value=extracao.suggested_type.value if extracao.suggested_type else tipos[0])
        cb_tipo = ttk.Combobox(frame, textvariable=var_tipo, values=tipos, state="readonly", width=28)
        cb_tipo.grid(row=0, column=1, padx=12, pady=(12, 2))

        # Competência
        tk.Label(frame, text="Competência:", font=("Segoe UI", 9, "bold"),
                 bg=COR_PANEL, fg="#a6adc8").grid(row=1, column=0, sticky="w", padx=12, pady=6)

        var_comp = tk.StringVar(value=extracao.suggested_competence or "")
        tk.Entry(frame, textvariable=var_comp, font=("Segoe UI", 10),
                 bg="#13131f", fg=COR_TEXT, insertbackground=COR_TEXT,
                 relief="flat", width=22).grid(row=1, column=1, padx=12, pady=6)

        # Confiança visual
        conf_cor = "#a6e3a1" if extracao.confidence >= 0.6 else "#f9e2af"
        tk.Label(popup, text=f"Confiança da leitura automática: {extracao.confidence:.0%}",
                 font=("Segoe UI", 9), bg=COR_BG, fg=conf_cor).pack(pady=(12, 0))

        # Botões
        frame_btn = tk.Frame(popup, bg=COR_BG)
        frame_btn.pack(pady=16)

        def confirmar():
            resultado["tipo"] = DocumentType(var_tipo.get())
            resultado["competencia"] = var_comp.get() or "Não informada"
            popup.destroy()

        def cancelar():
            popup.destroy()

        tk.Button(frame_btn, text="✓ Confirmar", font=("Segoe UI", 10, "bold"),
                  bg=COR_ACCENT, fg="white", relief="flat", padx=16, pady=6,
                  cursor="hand2", command=confirmar).pack(side="left", padx=8)

        tk.Button(frame_btn, text="Ignorar PDF", font=("Segoe UI", 10),
                  bg="#313244", fg="#a6adc8", relief="flat", padx=16, pady=6,
                  cursor="hand2", command=cancelar).pack(side="left", padx=8)

        popup.wait_window()
        return resultado["tipo"], resultado["competencia"]

    def _remover_documento(self):
        sel = self.lista_box.curselection()
        if not sel:
            return
        idx = sel[0]
        doc = self.documentos.pop(idx)
        self.lista_box.delete(idx)
        self._log(f"   🗑 Removido: {doc.filename}", "warn")
        self._atualizar_botao_enviar()

    def _atualizar_botao_enviar(self):
        estado = "normal" if self.documentos else "disabled"
        self.btn_enviar.config(state=estado)

    # ── ENVIO ─────────────────────────────────────────────────────────

    def _confirmar_e_enviar(self):
        if not self.documentos:
            messagebox.showwarning("Sem documentos", "Adicione pelo menos 1 PDF antes de enviar.")
            return

        competencia = self.var_competencia.get() or "Não informada"
        empresa     = self.var_empresa.get() or "Empresa de Teste"

        resumo = (
            f"Você está prestes a enviar um e-mail REAL:\n\n"
            f"De:  {GMAIL_REMETENTE}\n"
            f"Para: {EMAIL_DESTINATARIO}\n"
            f"Empresa detectada: {empresa}\n"
            f"Competência: {competencia}\n"
            f"Documentos: {len(self.documentos)} arquivo(s)\n\n"
            f"Confirma o envio?"
        )
        if not messagebox.askyesno("Confirmar envio", resumo):
            return

        self._log(f"\n{'═'*48}", "info")
        self._log("🚀 INICIANDO ENVIO REAL VIA GMAIL SMTP", "bold")
        self._log(f"   Timestamp : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self._log(f"   De        : {GMAIL_REMETENTE}")
        self._log(f"   Para      : {EMAIL_DESTINATARIO}")
        self._log(f"   Documentos: {len(self.documentos)}")

        try:
            msg = self._montar_email(empresa, competencia)
            self._enviar_smtp(msg)

            self._log("", "ok")
            self._log("✅ E-MAIL ENVIADO COM SUCESSO!", "ok")
            self._log(f"   Verifique sua caixa: {EMAIL_DESTINATARIO}", "ok")
            self._log(f"{'═'*48}", "info")
            messagebox.showinfo("Sucesso!", f"E-mail enviado!\nVerifique: {EMAIL_DESTINATARIO}")

        except smtplib.SMTPAuthenticationError:
            self._log("❌ ERRO DE AUTENTICAÇÃO", "err")
            self._log("   Verifique GMAIL_APP_PASSWORD no topo do script.", "err")
            self._log("   Lembre: use App Password, não sua senha normal.", "err")
            messagebox.showerror("Erro de autenticação",
                "Senha incorreta.\n\nUse um App Password do Google:\nmyaccount.google.com/apppasswords")

        except Exception as e:
            self._log(f"❌ ERRO: {str(e)}", "err")
            messagebox.showerror("Erro no envio", str(e))

    def _montar_email(self, empresa: str, competencia: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_REMETENTE
        msg["To"]      = EMAIL_DESTINATARIO
        msg["Subject"] = f"[TESTE] Guias — {empresa} — Competência: {competencia}"

        # Lista de documentos no corpo
        lista_docs = "\n".join(
            f"  - {d.tipo.value}: {d.filename} ({d.size_kb:.1f} KB)"
            for d in self.documentos
        )

        corpo = (
            f"Este é um e-mail de TESTE do Sistema de Guias.\n\n"
            f"Empresa: {empresa}\n"
            f"Competência: {competencia}\n\n"
            f"Documentos em anexo:\n{lista_docs}\n\n"
            f"---\n"
            f"Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n"
            f"Sistema de Guias — Demo"
        )
        msg.attach(MIMEText(corpo, "plain", "utf-8"))

        # Anexa os PDFs reais
        for doc in self.documentos:
            with open(doc.caminho, "rb") as f:
                parte = MIMEApplication(f.read(), _subtype="pdf")
                parte.add_header("Content-Disposition", "attachment", filename=doc.filename)
                msg.attach(parte)
            self._log(f"   📎 Anexado: {doc.filename} ({doc.size_kb:.1f} KB)")

        return msg

    def _enviar_smtp(self, msg: MIMEMultipart):
        self._log("   Conectando ao Gmail SMTP (smtp.gmail.com:587)...")
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            self._log("   Autenticando...")
            server.login(GMAIL_REMETENTE, GMAIL_APP_PASSWORD)
            self._log("   Autenticado! Enviando mensagem...")
            server.sendmail(GMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())

    # ── LOG ───────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = ""):
        self.log_text.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        linha = f"[{ts}] {msg}\n" if msg.strip() else "\n"
        self.log_text.insert("end", linha, tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update_idletasks()


# ── MAIN ──────────────────────────────────────────────────────────────

def validar_config():
    erros = []
    if "seuemail" in GMAIL_REMETENTE:
        erros.append("• Preencha GMAIL_REMETENTE com seu e-mail real")
    if "xxxx" in GMAIL_APP_PASSWORD:
        erros.append("• Preencha GMAIL_APP_PASSWORD com seu App Password do Google")
    return erros

if __name__ == "__main__":
    erros = validar_config()
    if erros:
        print("\n⚠ Configure o script antes de rodar:\n")
        for e in erros:
            print(f"  {e}")
        print("\nEdite as 3 variáveis no topo do arquivo demo_gui.py\n")
        sys.exit(1)

    root = tk.Tk()
    app = DemoApp(root)
    root.mainloop()

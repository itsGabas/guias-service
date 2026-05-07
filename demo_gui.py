"""
DEMO GUI — Sistema de Guias
Aba 1: Gerenciar Templates de Tarefas
Aba 2: Upload de PDFs + Envio
"""
import os, sys, uuid, smtplib, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.services.pdf_service import PDFService
from app.models.enums import DocumentType, Department
from app.models.task_template import TaskTemplate
from app.repositories.mock_repository import MockRepository
from mock_data.clients import MOCK_CLIENTS

# ══════════════════════════════════════════════════════════════════════
GMAIL_REMETENTE    = "seuemail@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
EMAIL_DESTINATARIO = "seuemail@gmail.com"
# ══════════════════════════════════════════════════════════════════════

BG=("#1e1e2e"); PANEL=("#2a2a3e"); ACCENT=("#7c6af7"); TEXT=("#cdd6f4")
SUB=("#a6adc8"); OK=("#a6e3a1"); WARN=("#f9e2af"); ERR=("#f38ba8")
DARK=("#13131f"); BTN2=("#313244"); GREEN=("#40a060")


class DocumentoDetectado:
    def __init__(self, caminho, extracao, tipo, competencia, template=None, client=None):
        self.caminho=caminho; self.filename=os.path.basename(caminho)
        self.size_kb=os.path.getsize(caminho)/1024; self.extracao=extracao
        self.tipo=tipo; self.competencia=competencia
        self.template=template; self.client=client


class DemoApp:
    def __init__(self, root):
        self.root=root; self.root.title("Sistema de Guias")
        self.root.geometry("780x700"); self.root.resizable(False,False)
        self.root.configure(bg=BG)
        self.pdf_svc=PDFService(); self.repo=MockRepository()
        self.documentos=[]; self.keywords_atual=[]
        for c in MOCK_CLIENTS: self.repo.save_client(c)
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root,text="📄 Sistema de Guias",font=("Segoe UI",14,"bold"),bg=BG,fg=TEXT).pack(pady=(16,2))
        tk.Label(self.root,text="Gerencie templates e envie guias aos clientes",font=("Segoe UI",9),bg=BG,fg=SUB).pack(pady=(0,10))
        style=ttk.Style(); style.theme_use("clam")
        style.configure("TNotebook",background=BG,borderwidth=0)
        style.configure("TNotebook.Tab",background=PANEL,foreground=SUB,padding=[16,6],font=("Segoe UI",10))
        style.map("TNotebook.Tab",background=[("selected",ACCENT)],foreground=[("selected","white")])
        nb=ttk.Notebook(self.root); nb.pack(fill="both",expand=True,padx=16,pady=(0,12))
        self.frame_templates=tk.Frame(nb,bg=BG); self.frame_upload=tk.Frame(nb,bg=BG)
        nb.add(self.frame_templates,text="  📋 Templates de Tarefas  ")
        nb.add(self.frame_upload,text="  📤 Upload & Envio  ")
        self._build_aba_templates(); self._build_aba_upload()

    # ══════════════════════════════════════════════════════════════════
    # ABA 1 — TEMPLATES
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_templates(self):
        f=self.frame_templates
        form=tk.Frame(f,bg=PANEL); form.pack(fill="x",padx=16,pady=(14,0))
        tk.Label(form,text="CRIAR TEMPLATE DE TAREFA",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=0,columnspan=4,sticky="w",padx=12,pady=(10,6))
        tk.Label(form,text="Nome*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        self.var_tpl_nome=tk.StringVar()
        tk.Entry(form,textvariable=self.var_tpl_nome,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=32).grid(row=1,column=1,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Depto*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=1,column=2,sticky="w",padx=12,pady=4)
        self.var_tpl_depto=tk.StringVar(value=Department.FISCAL.value)
        ttk.Combobox(form,textvariable=self.var_tpl_depto,values=[d.value for d in Department],
                     state="readonly",width=14).grid(row=1,column=3,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Criado por*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=2,column=0,sticky="w",padx=12,pady=4)
        self.var_tpl_criador=tk.StringVar()
        tk.Entry(form,textvariable=self.var_tpl_criador,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=22).grid(row=2,column=1,sticky="w",padx=6,pady=4)

        kw_frame=tk.Frame(f,bg=PANEL); kw_frame.pack(fill="x",padx=16,pady=(10,0))
        tk.Label(kw_frame,text="PALAVRAS-CHAVE  (PDF deve conter TODAS)",
                 font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(10,2))
        tk.Label(kw_frame,text="Use termos fixos presentes em TODOS os PDFs desse tipo. Evite CNPJ, IE, nomes e datas variáveis.",
                 font=("Segoe UI",8),bg=PANEL,fg=SUB,wraplength=700,justify="left").pack(anchor="w",padx=12,pady=(0,6))
        row_kw=tk.Frame(kw_frame,bg=PANEL); row_kw.pack(fill="x",padx=12,pady=(0,6))
        self.var_kw_input=tk.StringVar()
        self.entry_kw=tk.Entry(row_kw,textvariable=self.var_kw_input,font=("Segoe UI",10),
                                bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=38)
        self.entry_kw.pack(side="left")
        self.entry_kw.bind("<Return>",lambda e: self._add_keyword())
        tk.Button(row_kw,text="+ Adicionar",font=("Segoe UI",9,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=12,pady=4,cursor="hand2",command=self._add_keyword).pack(side="left",padx=(8,0))
        self.frame_kw_lista=tk.Frame(kw_frame,bg=PANEL); self.frame_kw_lista.pack(fill="x",padx=12,pady=(0,10))

        btn_frame=tk.Frame(f,bg=BG); btn_frame.pack(fill="x",padx=16,pady=(10,0))
        tk.Button(btn_frame,text="📄 Validar com PDF modelo",font=("Segoe UI",9),bg=BTN2,fg=TEXT,
                  relief="flat",padx=14,pady=6,cursor="hand2",command=self._validar_com_modelo).pack(side="left",padx=(0,8))
        tk.Button(btn_frame,text="💾 Salvar Template",font=("Segoe UI",10,"bold"),bg=GREEN,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=self._salvar_template).pack(side="left")
        self.var_validacao=tk.StringVar(value="")
        tk.Label(btn_frame,textvariable=self.var_validacao,font=("Segoe UI",9),bg=BG,fg=OK).pack(side="left",padx=12)

        saved=tk.Frame(f,bg=PANEL); saved.pack(fill="both",expand=True,padx=16,pady=(14,14))
        tk.Label(saved,text="TEMPLATES SALVOS",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).pack(anchor="w",padx=12,pady=(10,4))
        self.lista_templates=tk.Listbox(saved,font=("Consolas",9),bg=DARK,fg=TEXT,
                                         selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0,height=7)
        self.lista_templates.pack(fill="both",expand=True,padx=12,pady=(0,4))
        tk.Button(saved,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=self._remover_template
                  ).pack(anchor="e",padx=12,pady=(0,8))

    def _add_keyword(self):
        kw=self.var_kw_input.get().strip()
        if not kw: return
        if kw.lower() in [k.lower() for k in self.keywords_atual]:
            messagebox.showwarning("Duplicada",f"'{kw}' já foi adicionada."); return
        self.keywords_atual.append(kw); self.var_kw_input.set(""); self._render_keywords()

    def _render_keywords(self):
        for w in self.frame_kw_lista.winfo_children(): w.destroy()
        for kw in self.keywords_atual:
            row=tk.Frame(self.frame_kw_lista,bg=PANEL); row.pack(anchor="w",pady=1)
            tk.Label(row,text=f"  ✦ {kw}",font=("Consolas",9),bg=BTN2,fg=WARN,padx=8,pady=3).pack(side="left")
            tk.Button(row,text="✕",font=("Segoe UI",8),bg=ERR,fg="white",relief="flat",padx=4,
                      cursor="hand2",command=lambda k=kw: self._remove_keyword(k)).pack(side="left",padx=(2,0))

    def _remove_keyword(self,kw):
        self.keywords_atual=[k for k in self.keywords_atual if k!=kw]; self._render_keywords()

    def _validar_com_modelo(self):
        if not self.keywords_atual:
            messagebox.showwarning("Sem regras","Adicione pelo menos uma palavra-chave antes de validar."); return
        caminho=filedialog.askopenfilename(title="Selecione o PDF modelo",filetypes=[("PDF","*.pdf")])
        if not caminho: return
        extracao=self.pdf_svc.extract_from_file(caminho)
        text_lower=extracao.raw_text.lower()
        encontradas=[kw for kw in self.keywords_atual if kw.lower() in text_lower]
        faltando=[kw for kw in self.keywords_atual if kw.lower() not in text_lower]
        if not faltando:
            self.var_validacao.set(f"✅ Válido — todas as {len(encontradas)} regras encontradas")
        else:
            self.var_validacao.set(f"⚠ {len(faltando)} regra(s) não encontrada(s)")
            messagebox.showwarning("Validação falhou",
                "Palavras-chave NÃO encontradas no PDF:\n\n"
                +"\n".join(f"  • {k}" for k in faltando)
                +"\n\nRevise as regras ou escolha outro PDF modelo.")

    def _salvar_template(self):
        nome=self.var_tpl_nome.get().strip(); criador=self.var_tpl_criador.get().strip()
        if not nome: messagebox.showwarning("Campo obrigatório","Informe o nome da tarefa."); return
        if not criador: messagebox.showwarning("Campo obrigatório","Informe quem está criando."); return
        if not self.keywords_atual: messagebox.showwarning("Sem regras","Adicione pelo menos uma palavra-chave."); return
        template=TaskTemplate(id=str(uuid.uuid4())[:8],name=nome,
                               department=Department(self.var_tpl_depto.get()),
                               keywords=list(self.keywords_atual),created_by=criador)
        self.repo.save_template(template)
        self.var_tpl_nome.set(""); self.var_tpl_criador.set("")
        self.keywords_atual=[]; self._render_keywords(); self.var_validacao.set("")
        self._atualizar_lista_templates()
        messagebox.showinfo("Salvo!",f"Template '{nome}' salvo com {len(template.keywords)} regra(s).")

    def _atualizar_lista_templates(self):
        self.lista_templates.delete(0,"end")
        for t in self.repo.list_templates():
            self.lista_templates.insert("end",
                f"  ○  [{t.department.value}]  {t.name}  —  {len(t.keywords)} regra(s)  (ID: {t.id})")

    def _remover_template(self):
        sel=self.lista_templates.curselection()
        if not sel: return
        t=self.repo.list_templates()[sel[0]]
        if messagebox.askyesno("Remover",f"Remover template '{t.name}'?"):
            self.repo.delete_template(t.id); self._atualizar_lista_templates()

    # ══════════════════════════════════════════════════════════════════
    # ABA 2 — UPLOAD & ENVIO
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_upload(self):
        f=self.frame_upload
        tk.Button(f,text="+ Selecionar PDF(s)",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=18,pady=8,cursor="hand2",command=self._selecionar_pdfs).pack(pady=(16,0))

        frame_lista=tk.Frame(f,bg=PANEL); frame_lista.pack(fill="x",padx=16,pady=(12,0))
        tk.Label(frame_lista,text="Documentos adicionados:",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,2))
        self.lista_docs=tk.Listbox(frame_lista,height=5,font=("Consolas",9),bg=DARK,fg=TEXT,
                                    selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0)
        self.lista_docs.pack(fill="x",padx=10,pady=(0,4))
        tk.Button(frame_lista,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=self._remover_doc
                  ).pack(anchor="e",padx=10,pady=(0,8))

        frame_info=tk.Frame(f,bg=PANEL); frame_info.pack(fill="x",padx=16,pady=(8,0))
        tk.Label(frame_info,text="Empresa:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=0,sticky="w",padx=10,pady=(8,2))
        self.var_empresa=tk.StringVar(value="—")
        tk.Label(frame_info,textvariable=self.var_empresa,font=("Segoe UI",10),bg=PANEL,fg=OK
                 ).grid(row=0,column=1,sticky="w",padx=6,pady=(8,2))
        tk.Label(frame_info,text="Identificado por:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=2,sticky="w",padx=10,pady=(8,2))
        self.var_id_tipo=tk.StringVar(value="—")
        tk.Label(frame_info,textvariable=self.var_id_tipo,font=("Segoe UI",9),bg=PANEL,fg=WARN
                 ).grid(row=0,column=3,sticky="w",padx=6,pady=(8,2))
        tk.Label(frame_info,text="Competência:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=1,column=0,sticky="w",padx=10,pady=4)
        self.var_competencia=tk.StringVar()
        tk.Entry(frame_info,textvariable=self.var_competencia,font=("Segoe UI",10),
                 bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=20
                 ).grid(row=1,column=1,sticky="w",padx=6,pady=4)

        frame_log=tk.Frame(f,bg=PANEL); frame_log.pack(fill="both",expand=True,padx=16,pady=(12,0))
        tk.Label(frame_log,text="Log:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).pack(anchor="w",padx=10,pady=(8,2))
        self.log_text=tk.Text(frame_log,height=9,font=("Consolas",9),bg=DARK,fg=TEXT,
                               relief="flat",bd=0,highlightthickness=0,state="disabled",wrap="word")
        self.log_text.pack(fill="both",expand=True,padx=10,pady=(0,10))
        for tag,cor in [("ok",OK),("warn",WARN),("err",ERR),("info","#89b4fa"),("bold",None)]:
            if cor: self.log_text.tag_config(tag,foreground=cor)
            else: self.log_text.tag_config(tag,font=("Consolas",9,"bold"))

        self.btn_enviar=tk.Button(f,text="🚀 Enviar E-mail de Teste",
                                   font=("Segoe UI",11,"bold"),bg=GREEN,fg="white",
                                   relief="flat",padx=20,pady=10,cursor="hand2",
                                   command=self._confirmar_e_enviar,state="disabled")
        self.btn_enviar.pack(pady=12)

    def _selecionar_pdfs(self):
        caminhos=filedialog.askopenfilenames(title="Selecione os PDFs",filetypes=[("PDF","*.pdf")])
        for c in caminhos: self._processar_pdf(c)
        self.btn_enviar.config(state="normal" if self.documentos else "disabled")

    def _processar_pdf(self,caminho):
        filename=os.path.basename(caminho)
        self._log(f"\n{'─'*46}","info")
        self._log(f"📄 {filename}","bold")

        # Passa lista de clientes para o PDFService tentar identificar automaticamente
        clientes=self.repo.list_clients()
        extracao=self.pdf_svc.extract_from_file(caminho, clients=clientes)
        template=self.repo.match_template(extracao.raw_text)

        self._log(f"   Confiança   : {extracao.confidence:.0%}","ok" if extracao.confidence>=0.6 else "warn")
        self._log(f"   Tipo        : {extracao.suggested_type.value if extracao.suggested_type else '❓'}",
                  "ok" if extracao.suggested_type else "warn")
        self._log(f"   Competência : {extracao.suggested_competence or '❓'}",
                  "ok" if extracao.suggested_competence else "warn")

        # Log do identificador da empresa
        client_detectado = None
        if extracao.client_match and extracao.client_match.client:
            client_detectado = extracao.client_match.client
            metodo = "CNPJ" if extracao.client_match.matched_by == "cnpj" else "Inscrição Estadual"
            self._log(f"   Empresa     : {client_detectado.company_name} ✅","ok")
            self._log(f"   Identificado: via {metodo} — {extracao.client_match.matched_value}","ok")
        elif extracao.suggested_company_cnpj:
            self._log(f"   CNPJ        : {extracao.suggested_company_cnpj} (cliente não cadastrado)","warn")
        elif extracao.suggested_company_ie:
            self._log(f"   IE          : {extracao.suggested_company_ie} (cliente não cadastrado)","warn")
        else:
            self._log("   Empresa     : ❓ Não identificada — seleção manual necessária","err")

        if template:
            self._log(f"   Template    : '{template.name}' [{template.department.value}]","ok")
        else:
            self._log("   Template    : ⚠ Nenhum vinculado","warn")

        # Popup de confirmação
        tipo_final,comp_final,client_final=self._janela_confirmacao(filename,extracao,template,client_detectado)
        if tipo_final is None:
            self._log("   ↩ Ignorado.","warn"); return

        doc=DocumentoDetectado(caminho,extracao,tipo_final,comp_final,template,client_final)
        self.documentos.append(doc)

        lbl=f" → {template.name}" if template else ""
        self.lista_docs.insert("end",f"  ✓  {doc.tipo.value:<20} {doc.filename}{lbl}")

        # Atualiza painel de info
        if client_final and self.var_empresa.get()=="—":
            self.var_empresa.set(client_final.company_name)
            metodo="CNPJ" if (extracao.client_match and extracao.client_match.matched_by=="cnpj") else "IE"
            self.var_id_tipo.set(metodo)
        elif extracao.suggested_company_cnpj and self.var_empresa.get()=="—":
            self.var_empresa.set(extracao.suggested_company_cnpj)
            self.var_id_tipo.set("CNPJ (não cadastrado)")
        elif extracao.suggested_company_ie and self.var_empresa.get()=="—":
            self.var_empresa.set(extracao.suggested_company_ie)
            self.var_id_tipo.set("IE (não cadastrada)")

        if extracao.suggested_competence and not self.var_competencia.get():
            self.var_competencia.set(extracao.suggested_competence)

        self._log(f"   ✅ Adicionado: {doc.tipo.value} — {comp_final}","ok")

    def _janela_confirmacao(self,filename,extracao,template,client_detectado):
        popup=tk.Toplevel(self.root); popup.title("Confirmar dados")
        popup.geometry("520x440"); popup.configure(bg=BG); popup.grab_set()
        resultado={"tipo":None,"competencia":None,"client":client_detectado}

        tk.Label(popup,text="Confirme os dados detectados",font=("Segoe UI",11,"bold"),bg=BG,fg=TEXT).pack(pady=(16,2))
        tk.Label(popup,text=filename,font=("Consolas",9),bg=BG,fg=SUB).pack()

        if template:
            tk.Label(popup,text=f"✅ Template: {template.name}",
                     font=("Segoe UI",9,"bold"),bg=BG,fg=OK).pack(pady=(4,0))
        else:
            tk.Label(popup,text="⚠ Nenhum template vinculado",
                     font=("Segoe UI",9),bg=BG,fg=WARN).pack(pady=(4,0))

        frame=tk.Frame(popup,bg=PANEL); frame.pack(fill="x",padx=20,pady=10)

        # Tipo
        tk.Label(frame,text="Tipo:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=0,sticky="w",padx=12,pady=(12,4))
        tipos=[d.value for d in DocumentType]
        var_tipo=tk.StringVar(value=extracao.suggested_type.value if extracao.suggested_type else tipos[0])
        ttk.Combobox(frame,textvariable=var_tipo,values=tipos,state="readonly",width=28
                     ).grid(row=0,column=1,padx=12,pady=(12,4))

        # Competência
        tk.Label(frame,text="Competência:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        var_comp=tk.StringVar(value=extracao.suggested_competence or "")
        tk.Entry(frame,textvariable=var_comp,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=22).grid(row=1,column=1,padx=12,pady=4)

        # Cliente — mostra detectado ou dropdown para seleção manual
        tk.Label(frame,text="Cliente:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=2,column=0,sticky="w",padx=12,pady=4)

        clientes=self.repo.list_clients()
        opcoes_clientes=["— Selecionar manualmente —"] + [f"{c.company_name} ({c.cnpj})" for c in clientes]

        if client_detectado:
            idx=next((i+1 for i,c in enumerate(clientes) if c.id==client_detectado.id),0)
            id_label="CNPJ" if (extracao.client_match and extracao.client_match.matched_by=="cnpj") else "IE"
            tk.Label(frame,text=f"✅ {client_detectado.company_name} (via {id_label})",
                     font=("Segoe UI",9),bg=PANEL,fg=OK).grid(row=2,column=1,sticky="w",padx=12,pady=4)
            var_client_idx=tk.IntVar(value=idx)
            # Botão para trocar manualmente mesmo que tenha detectado
            def abrir_troca():
                self._janela_troca_cliente(clientes,resultado,popup)
            tk.Button(frame,text="Trocar",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                      relief="flat",cursor="hand2",command=abrir_troca
                      ).grid(row=2,column=2,padx=6,pady=4)
        else:
            # Nenhum cliente identificado — dropdown obrigatório
            var_client_str=tk.StringVar(value=opcoes_clientes[0])
            cb=ttk.Combobox(frame,textvariable=var_client_str,values=opcoes_clientes,
                             state="readonly",width=34)
            cb.grid(row=2,column=1,padx=12,pady=4)
            tk.Label(frame,text="⚠ Selecione o cliente",font=("Segoe UI",8),
                     bg=PANEL,fg=WARN).grid(row=3,column=1,sticky="w",padx=12)

            def on_client_change(*_):
                sel=var_client_str.get()
                if sel.startswith("—"):
                    resultado["client"]=None; return
                idx=opcoes_clientes.index(sel)-1
                resultado["client"]=clientes[idx]
            var_client_str.trace_add("write",on_client_change)

        # Confiança
        tk.Label(popup,text=f"Confiança da leitura: {extracao.confidence:.0%}",font=("Segoe UI",9),
                 bg=BG,fg=OK if extracao.confidence>=0.6 else WARN).pack(pady=(6,0))

        # Warnings
        if extracao.warnings:
            for w in extracao.warnings:
                tk.Label(popup,text=f"⚠ {w}",font=("Segoe UI",8),bg=BG,fg=WARN,wraplength=460).pack()

        frame_btn=tk.Frame(popup,bg=BG); frame_btn.pack(pady=14)

        def confirmar():
            resultado["tipo"]=DocumentType(var_tipo.get())
            resultado["competencia"]=var_comp.get() or "Não informada"
            popup.destroy()

        tk.Button(frame_btn,text="✓ Confirmar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=confirmar).pack(side="left",padx=8)
        tk.Button(frame_btn,text="Ignorar PDF",font=("Segoe UI",10),bg=BTN2,fg=SUB,
                  relief="flat",padx=16,pady=6,cursor="hand2",command=popup.destroy).pack(side="left",padx=8)

        popup.wait_window()
        return resultado["tipo"],resultado["competencia"],resultado["client"]

    def _janela_troca_cliente(self,clientes,resultado,parent):
        popup=tk.Toplevel(parent); popup.title("Trocar cliente")
        popup.geometry("420x200"); popup.configure(bg=BG); popup.grab_set()
        tk.Label(popup,text="Selecione o cliente correto:",font=("Segoe UI",10,"bold"),bg=BG,fg=TEXT).pack(pady=(16,8))
        opcoes=["— Nenhum —"]+[f"{c.company_name} ({c.cnpj})" for c in clientes]
        var=tk.StringVar(value=opcoes[0])
        ttk.Combobox(popup,textvariable=var,values=opcoes,state="readonly",width=44).pack(padx=20)
        def confirmar():
            sel=var.get()
            if not sel.startswith("—"):
                idx=opcoes.index(sel)-1
                resultado["client"]=clientes[idx]
            popup.destroy()
        tk.Button(popup,text="Confirmar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=confirmar).pack(pady=16)
        popup.wait_window()

    def _remover_doc(self):
        sel=self.lista_docs.curselection()
        if not sel: return
        doc=self.documentos.pop(sel[0]); self.lista_docs.delete(sel[0])
        self._log(f"   🗑 Removido: {doc.filename}","warn")
        self.btn_enviar.config(state="normal" if self.documentos else "disabled")

    # ── ENVIO ─────────────────────────────────────────────────────────

    def _confirmar_e_enviar(self):
        competencia=self.var_competencia.get() or "Não informada"
        empresa=self.var_empresa.get() or "Empresa de Teste"
        if not messagebox.askyesno("Confirmar envio",
            f"Enviar e-mail REAL?\n\nDe: {GMAIL_REMETENTE}\nPara: {EMAIL_DESTINATARIO}\n"
            f"Empresa: {empresa}\nCompetência: {competencia}\nDocumentos: {len(self.documentos)}"): return
        self._log(f"\n{'═'*46}","info"); self._log("🚀 ENVIANDO VIA GMAIL SMTP...","bold")
        try:
            msg=self._montar_email(empresa,competencia)
            self._enviar_smtp(msg)
            self._log("✅ E-MAIL ENVIADO COM SUCESSO!","ok")
            self._log(f"   Verifique: {EMAIL_DESTINATARIO}","ok")
            messagebox.showinfo("Sucesso!",f"E-mail enviado!\nVerifique: {EMAIL_DESTINATARIO}")
        except smtplib.SMTPAuthenticationError:
            self._log("❌ Erro de autenticação — verifique o App Password","err")
            messagebox.showerror("Erro","App Password incorreto.")
        except Exception as e:
            self._log(f"❌ Erro: {e}","err"); messagebox.showerror("Erro no envio",str(e))

    def _montar_email(self,empresa,competencia):
        msg=MIMEMultipart(); msg["From"]=GMAIL_REMETENTE
        msg["To"]=EMAIL_DESTINATARIO
        msg["Subject"]=f"[TESTE] Guias — {empresa} — {competencia}"
        lista="\n".join(f"  - {d.tipo.value}: {d.filename} ({d.size_kb:.1f} KB)" for d in self.documentos)
        corpo=(f"E-mail de TESTE do Sistema de Guias.\n\nEmpresa: {empresa}\n"
               f"Competência: {competencia}\n\nDocumentos:\n{lista}\n\n"
               f"Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
        msg.attach(MIMEText(corpo,"plain","utf-8"))
        for doc in self.documentos:
            with open(doc.caminho,"rb") as f:
                parte=MIMEApplication(f.read(),_subtype="pdf")
                parte.add_header("Content-Disposition","attachment",filename=doc.filename)
                msg.attach(parte)
            self._log(f"   📎 Anexado: {doc.filename} ({doc.size_kb:.1f} KB)")
        return msg

    def _enviar_smtp(self,msg):
        with smtplib.SMTP("smtp.gmail.com",587) as s:
            s.ehlo(); s.starttls()
            s.login(GMAIL_REMETENTE,GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_REMETENTE,EMAIL_DESTINATARIO,msg.as_string())

    def _log(self,msg,tag=""):
        self.log_text.config(state="normal")
        ts=datetime.now().strftime("%H:%M:%S")
        line=f"[{ts}] {msg}\n" if msg.strip() else "\n"
        self.log_text.insert("end",line,tag); self.log_text.see("end")
        self.log_text.config(state="disabled"); self.root.update_idletasks()


if __name__=="__main__":
    erros=[]
    if "seuemail" in GMAIL_REMETENTE: erros.append("• Preencha GMAIL_REMETENTE")
    if "xxxx" in GMAIL_APP_PASSWORD: erros.append("• Preencha GMAIL_APP_PASSWORD")
    if erros:
        print("\n⚠ Configure antes de rodar:\n")
        for e in erros: print(f"  {e}")
        sys.exit(1)
    root=tk.Tk(); DemoApp(root); root.mainloop()

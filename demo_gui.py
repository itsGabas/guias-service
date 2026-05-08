"""
DEMO GUI — Sistema de Guias
Aba 1: Empresas (importar planilha + gerenciar e-mails por departamento)
Aba 2: Templates de Tarefas
Aba 3: Upload & Envio
"""
import os, sys, uuid, smtplib, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.services.pdf_service import PDFService
from app.services.xlsx_service import XlsxService
from app.models.enums import DocumentType, Department
from app.models.task_template import TaskTemplate
from app.repositories.mock_repository import MockRepository

# ══════════════════════════════════════════════════════════════════════
GMAIL_REMETENTE    = "xxxx"
GMAIL_APP_PASSWORD = "xxxx"
# ══════════════════════════════════════════════════════════════════════

BG=("#1e1e2e"); PANEL=("#2a2a3e"); ACCENT=("#7c6af7"); TEXT=("#cdd6f4")
SUB=("#a6adc8"); OK=("#a6e3a1"); WARN=("#f9e2af"); ERR=("#f38ba8")
DARK=("#13131f"); BTN2=("#313244"); GREEN=("#40a060")
ALL_DEPTS=[d.value for d in Department]


class DocumentoDetectado:
    def __init__(self, caminho, extracao, competencia, template=None, client=None):
        self.caminho=caminho; self.filename=os.path.basename(caminho)
        self.size_kb=os.path.getsize(caminho)/1024; self.extracao=extracao
        self.competencia=competencia; self.template=template; self.client=client


class DemoApp:
    def __init__(self, root):
        self.root=root; self.root.title("Sistema de Guias")
        self.root.geometry("860x740"); self.root.resizable(False,False)
        self.root.configure(bg=BG)
        self.pdf_svc=PDFService(); self.xlsx_svc=XlsxService()
        self.repo=MockRepository()
        self.documentos=[]; self.keywords_atual=[]
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root,text="📄 Sistema de Guias",font=("Segoe UI",14,"bold"),bg=BG,fg=TEXT).pack(pady=(14,2))
        tk.Label(self.root,text="Gerencie empresas, templates e envie guias",font=("Segoe UI",9),bg=BG,fg=SUB).pack(pady=(0,8))
        style=ttk.Style(); style.theme_use("clam")
        style.configure("TNotebook",background=BG,borderwidth=0)
        style.configure("TNotebook.Tab",background=PANEL,foreground=SUB,padding=[14,6],font=("Segoe UI",10))
        style.map("TNotebook.Tab",background=[("selected",ACCENT)],foreground=[("selected","white")])
        style.configure("Treeview",background=DARK,foreground=TEXT,fieldbackground=DARK,rowheight=22,font=("Consolas",9))
        style.configure("Treeview.Heading",background=PANEL,foreground=SUB,font=("Segoe UI",9,"bold"))
        style.map("Treeview",background=[("selected",ACCENT)])
        nb=ttk.Notebook(self.root); nb.pack(fill="both",expand=True,padx=14,pady=(0,10))
        self.frame_empresas=tk.Frame(nb,bg=BG)
        self.frame_templates=tk.Frame(nb,bg=BG)
        self.frame_upload=tk.Frame(nb,bg=BG)
        nb.add(self.frame_empresas,  text="  🏢 Empresas  ")
        nb.add(self.frame_templates, text="  📋 Templates  ")
        nb.add(self.frame_upload,    text="  📤 Upload & Envio  ")
        self._build_aba_empresas()
        self._build_aba_templates()
        self._build_aba_upload()

    # ══════════════════════════════════════════════════════════════════
    # ABA 1 — EMPRESAS
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_empresas(self):
        f=self.frame_empresas

        # Toolbar
        tb=tk.Frame(f,bg=BG); tb.pack(fill="x",padx=14,pady=(12,6))
        tk.Button(tb,text="📂 Importar Planilha (.xlsx)",font=("Segoe UI",10,"bold"),
                  bg=ACCENT,fg="white",relief="flat",padx=14,pady=7,cursor="hand2",
                  command=self._importar_planilha).pack(side="left")
        tk.Button(tb,text="✉ Gerenciar E-mails",font=("Segoe UI",9),
                  bg=GREEN,fg="white",relief="flat",padx=12,pady=7,cursor="hand2",
                  command=self._abrir_gerenciar_emails).pack(side="left",padx=(8,0))
        tk.Button(tb,text="🔄 Atualizar",font=("Segoe UI",9),
                  bg=BTN2,fg=TEXT,relief="flat",padx=10,pady=7,cursor="hand2",
                  command=self._atualizar_tabela).pack(side="left",padx=(8,0))
        self.var_total=tk.StringVar(value="0 empresas")
        tk.Label(tb,textvariable=self.var_total,font=("Segoe UI",9),bg=BG,fg=SUB).pack(side="right")

        # Busca
        bf=tk.Frame(f,bg=PANEL); bf.pack(fill="x",padx=14,pady=(0,6))
        tk.Label(bf,text="🔍",font=("Segoe UI",11),bg=PANEL,fg=SUB).pack(side="left",padx=(10,4),pady=6)
        self.var_busca=tk.StringVar()
        self.var_busca.trace_add("write",lambda *_: self._filtrar())
        tk.Entry(bf,textvariable=self.var_busca,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=44).pack(side="left",pady=6)
        tk.Label(bf,text="Buscar por nome, CNPJ, código ou IE",
                 font=("Segoe UI",8),bg=PANEL,fg=SUB).pack(side="left",padx=10)

        # Tabela principal
        tf=tk.Frame(f,bg=PANEL); tf.pack(fill="both",expand=True,padx=14,pady=(0,4))
        cols=("codigo","tipo","nome","cnpj","ie","emails")
        self.tree=ttk.Treeview(tf,columns=cols,show="headings",height=14)
        for col,lbl,w in zip(cols,["Cód.","Tipo","Nome","CNPJ","IE","E-mails cadastrados"],[55,55,230,150,130,195]):
            self.tree.heading(col,text=lbl,command=lambda c=col: self._sort(c))
            self.tree.column(col,width=w,minwidth=30)
        vsb=ttk.Scrollbar(tf,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left",fill="both",expand=True)
        vsb.pack(side="right",fill="y")
        self.tree.bind("<<TreeviewSelect>>",self._on_select)
        self.tree.bind("<Double-1>",lambda e: self._abrir_gerenciar_emails())

        # Painel detalhe / e-mails
        dp=tk.Frame(f,bg=PANEL); dp.pack(fill="x",padx=14,pady=(0,4))
        tk.Label(dp,text="E-mails da empresa selecionada:",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(6,2))
        self.var_emails_detalhe=tk.StringVar(value="Selecione uma empresa")
        tk.Label(dp,textvariable=self.var_emails_detalhe,font=("Consolas",8),
                 bg=PANEL,fg=OK,justify="left",wraplength=820).pack(anchor="w",padx=14,pady=(0,6))

        self.var_sync=tk.StringVar(value="")
        tk.Label(f,textvariable=self.var_sync,font=("Segoe UI",8),bg=BG,fg=WARN,
                 wraplength=820).pack(anchor="w",padx=14,pady=(0,4))

    def _importar_planilha(self):
        path=filedialog.askopenfilename(title="Selecione a planilha",
                                        filetypes=[("Excel","*.xlsx *.xlsm"),("Todos","*.*")])
        if not path: return
        total=len(self.repo.list_clients(active_only=False))
        if total>0:
            if not messagebox.askyesno("Confirmar sincronização",
                f"Já existem {total} empresa(s) cadastrada(s).\n\n"
                "✅ Novas serão inseridas\n🔄 Existentes serão atualizadas\n"
                "🗑 Removidas as que não estiverem na planilha\n\n"
                "Os e-mails já cadastrados serão preservados.\n\nContinuar?"): return

        # Preserva e-mails antes do sync
        emails_backup={c.cnpj_digits(): c.emails for c in self.repo.list_clients(active_only=False)}

        result=self.xlsx_svc.sync(path,self.repo)

        # Restaura e-mails preservados
        for c in self.repo.list_clients(active_only=False):
            if c.cnpj_digits() in emails_backup:
                c.emails=emails_backup[c.cnpj_digits()]
                self.repo.save_client(c)

        self.var_sync.set(
            f"Última importação: {os.path.basename(path)}  |  "
            f"✅ {len(result.inserted)} inseridos  🔄 {len(result.updated)} atualizados  "
            f"🗑 {len(result.deleted)} removidos"
            +(f"  ⚠ {len(result.errors)} erros" if result.errors else ""))
        self._atualizar_tabela()
        msg=f"Sincronização concluída!\n\n{result.summary()}\n\nTotal ativo: {len(self.repo.list_clients())} empresas"
        messagebox.showwarning("Concluído com avisos",msg) if result.errors else messagebox.showinfo("Concluído",msg)

    def _atualizar_tabela(self):
        self._filtrar()

    def _filtrar(self):
        q=self.var_busca.get().lower() if hasattr(self,"var_busca") else ""
        for item in self.tree.get_children(): self.tree.delete(item)
        clientes=self.repo.list_clients(active_only=False)
        filtrados=[c for c in clientes if
                   q in (c.company_name or "").lower() or q in (c.cnpj_digits() or "") or
                   q in (c.codigo or "").lower() or q in (c.ie_digits() or "")] if q else clientes
        for c in filtrados:
            tipo="CPF" if len(c.cnpj_digits())==11 else "CNPJ"
            n_emails=len(c.emails)
            emails_resumo=f"{n_emails} e-mail(s)" if n_emails else "— sem e-mails"
            self.tree.insert("","end",iid=c.id,values=(
                c.codigo or "—", tipo, c.company_name, c.mask_cnpj(),
                c.inscricao_estadual or "—", emails_resumo))
        total=len(clientes)
        self.var_total.set(f"{total} empresa(s)" + (f"  |  {len(filtrados)} exibida(s)" if q else ""))

    def _on_select(self,event):
        sel=self.tree.selection()
        if not sel: return
        c=self.repo.get_client(sel[0])
        if not c: return
        if not c.emails:
            self.var_emails_detalhe.set("Nenhum e-mail cadastrado. Clique em 'Gerenciar E-mails'.")
            return
        linhas=[]
        for ce in c.emails:
            deptos=", ".join(ce.departments) if ce.departments else "nenhum depto"
            linhas.append(f"  {ce.email}  [{ce.label}]  →  {deptos}")
        self.var_emails_detalhe.set("\n".join(linhas))

    def _sort(self,col):
        items=[(self.tree.set(k,col),k) for k in self.tree.get_children("")]
        items.sort(key=lambda x: x[0].lower())
        for i,(_,k) in enumerate(items): self.tree.move(k,"",i)

    # ── GERENCIAR E-MAILS ─────────────────────────────────────────────

    def _abrir_gerenciar_emails(self):
        sel=self.tree.selection()
        if not sel:
            messagebox.showinfo("","Selecione uma empresa na tabela primeiro.")
            return
        client=self.repo.get_client(sel[0])
        if not client: return
        self._janela_emails(client)

    def _janela_emails(self,client):
        win=tk.Toplevel(self.root)
        win.title(f"E-mails — {client.company_name}")
        win.geometry("680x560"); win.configure(bg=BG); win.grab_set()

        tk.Label(win,text=f"✉ Gerenciar E-mails",font=("Segoe UI",12,"bold"),bg=BG,fg=TEXT).pack(pady=(14,2))
        tk.Label(win,text=f"{client.company_name}  |  {client.mask_cnpj()}  |  Cód. {client.codigo}",
                 font=("Segoe UI",9),bg=BG,fg=SUB).pack(pady=(0,10))

        # Tabela de e-mails
        tf=tk.Frame(win,bg=PANEL); tf.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(tf,text="E-MAILS CADASTRADOS",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,4))

        cols=("email","label","deptos")
        etree=ttk.Treeview(tf,columns=cols,show="headings",height=7)
        for col,lbl,w in zip(cols,["E-mail","Rótulo","Departamentos"],[220,120,270]):
            etree.heading(col,text=lbl); etree.column(col,width=w,minwidth=40)
        etree.pack(fill="x",padx=10,pady=(0,4))

        def refresh_etree():
            for i in etree.get_children(): etree.delete(i)
            for ce in client.emails:
                deptos=", ".join(ce.departments) if ce.departments else "— nenhum"
                etree.insert("","end",values=(ce.email,ce.label,deptos))

        refresh_etree()

        # Botão remover
        def remover_email():
            sel_e=etree.selection()
            if not sel_e: return
            vals=etree.item(sel_e[0])["values"]
            email_sel=vals[0]
            if messagebox.askyesno("Remover",f"Remover '{email_sel}'?"):
                client.remove_email(email_sel)
                self.repo.save_client(client)
                refresh_etree()
                self._atualizar_tabela()
                self._on_select(None)

        tk.Button(tf,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=remover_email
                  ).pack(anchor="e",padx=10,pady=(0,8))

        # Formulário de adição
        form=tk.Frame(win,bg=PANEL); form.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(form,text="ADICIONAR E-MAIL",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).grid(row=0,column=0,columnspan=4,sticky="w",padx=12,pady=(10,6))

        tk.Label(form,text="E-mail*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        var_email=tk.StringVar()
        tk.Entry(form,textvariable=var_email,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=28
                 ).grid(row=1,column=1,sticky="w",padx=6,pady=4)

        tk.Label(form,text="Rótulo*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=1,column=2,sticky="w",padx=12,pady=4)
        var_label=tk.StringVar()
        tk.Entry(form,textvariable=var_label,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=16
                 ).grid(row=1,column=3,sticky="w",padx=6,pady=4)

        # Checkboxes de departamentos
        tk.Label(form,text="Departamentos*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=2,column=0,sticky="nw",padx=12,pady=(6,4))

        dept_frame=tk.Frame(form,bg=PANEL)
        dept_frame.grid(row=2,column=1,columnspan=3,sticky="w",padx=6,pady=(6,4))
        dept_vars={d: tk.BooleanVar() for d in ALL_DEPTS}
        for i,d in enumerate(ALL_DEPTS):
            tk.Checkbutton(dept_frame,text=d,variable=dept_vars[d],
                           font=("Segoe UI",9),bg=PANEL,fg=TEXT,
                           selectcolor=DARK,activebackground=PANEL,
                           cursor="hand2").grid(row=i//3,column=i%3,sticky="w",padx=6,pady=2)

        def adicionar():
            email=var_email.get().strip().lower()
            label=var_label.get().strip()
            deptos=[d for d,v in dept_vars.items() if v.get()]
            if not email:
                messagebox.showwarning("","Informe o e-mail."); return
            if not label:
                messagebox.showwarning("","Informe um rótulo (ex: Financeiro, Sócio)."); return
            if not deptos:
                messagebox.showwarning("","Selecione ao menos um departamento."); return
            if "@" not in email:
                messagebox.showwarning("","E-mail inválido."); return
            if any(ce.email==email for ce in client.emails):
                messagebox.showwarning("Duplicado",f"'{email}' já cadastrado."); return
            client.add_email(email,label,deptos)
            self.repo.save_client(client)
            var_email.set(""); var_label.set("")
            for v in dept_vars.values(): v.set(False)
            refresh_etree()
            self._atualizar_tabela()
            self._on_select(None)

        tk.Button(form,text="+ Adicionar E-mail",font=("Segoe UI",10,"bold"),
                  bg=GREEN,fg="white",relief="flat",padx=14,pady=6,cursor="hand2",
                  command=adicionar).grid(row=3,column=0,columnspan=4,pady=(8,12),padx=12,sticky="w")

        # Resumo por departamento
        resumo=tk.Frame(win,bg=PANEL); resumo.pack(fill="x",padx=16,pady=(0,12))
        tk.Label(resumo,text="RESUMO POR DEPARTAMENTO",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,4))

        self._render_resumo_dept(resumo,client)
        self._resumo_frame=resumo
        self._resumo_client=client

        def fechar():
            win.destroy()
            self._atualizar_tabela()
            self._on_select(None)

        tk.Button(win,text="✓ Fechar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=18,pady=7,cursor="hand2",command=fechar).pack(pady=4)

    def _render_resumo_dept(self,frame,client):
        for w in frame.winfo_children():
            if isinstance(w,tk.Label) and w.cget("text") not in ("RESUMO POR DEPARTAMENTO",):
                w.destroy()
        linhas=[]
        for d in ALL_DEPTS:
            emails=client.get_emails_for_department(d)
            if emails:
                linhas.append(f"  {d:<12} → {', '.join(emails)}")
        if linhas:
            tk.Label(frame,text="\n".join(linhas),font=("Consolas",8),
                     bg=PANEL,fg=OK,justify="left").pack(anchor="w",padx=14,pady=(0,8))
        else:
            tk.Label(frame,text="  Nenhum e-mail configurado ainda.",
                     font=("Segoe UI",8),bg=PANEL,fg=WARN).pack(anchor="w",padx=14,pady=(0,8))

    # ══════════════════════════════════════════════════════════════════
    # ABA 2 — TEMPLATES
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_templates(self):
        f=self.frame_templates
        form=tk.Frame(f,bg=PANEL); form.pack(fill="x",padx=14,pady=(14,0))
        tk.Label(form,text="CRIAR TEMPLATE DE TAREFA",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=0,columnspan=4,sticky="w",padx=12,pady=(10,6))
        tk.Label(form,text="Nome*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        self.var_tpl_nome=tk.StringVar()
        tk.Entry(form,textvariable=self.var_tpl_nome,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=32).grid(row=1,column=1,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Depto*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=1,column=2,sticky="w",padx=12,pady=4)
        self.var_tpl_depto=tk.StringVar(value=Department.FISCAL.value)
        ttk.Combobox(form,textvariable=self.var_tpl_depto,values=ALL_DEPTS,
                     state="readonly",width=14).grid(row=1,column=3,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Criado por*",font=("Segoe UI",9),bg=PANEL,fg=TEXT).grid(row=2,column=0,sticky="w",padx=12,pady=4)
        self.var_tpl_criador=tk.StringVar()
        tk.Entry(form,textvariable=self.var_tpl_criador,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=22).grid(row=2,column=1,sticky="w",padx=6,pady=4)

        kw_frame=tk.Frame(f,bg=PANEL); kw_frame.pack(fill="x",padx=14,pady=(10,0))
        tk.Label(kw_frame,text="PALAVRAS-CHAVE  (PDF deve conter TODAS)",
                 font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(10,2))
        tk.Label(kw_frame,text="Use termos fixos. Evite CNPJ, IE, nomes e datas variáveis.",
                 font=("Segoe UI",8),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(0,6))
        row_kw=tk.Frame(kw_frame,bg=PANEL); row_kw.pack(fill="x",padx=12,pady=(0,6))
        self.var_kw_input=tk.StringVar()
        self.entry_kw=tk.Entry(row_kw,textvariable=self.var_kw_input,font=("Segoe UI",10),
                                bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=38)
        self.entry_kw.pack(side="left")
        self.entry_kw.bind("<Return>",lambda e: self._add_keyword())
        tk.Button(row_kw,text="+ Adicionar",font=("Segoe UI",9,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=12,pady=4,cursor="hand2",command=self._add_keyword).pack(side="left",padx=(8,0))
        self.frame_kw_lista=tk.Frame(kw_frame,bg=PANEL); self.frame_kw_lista.pack(fill="x",padx=12,pady=(0,10))

        btn_frame=tk.Frame(f,bg=BG); btn_frame.pack(fill="x",padx=14,pady=(8,0))
        tk.Button(btn_frame,text="📄 Validar com PDF modelo",font=("Segoe UI",9),bg=BTN2,fg=TEXT,
                  relief="flat",padx=14,pady=6,cursor="hand2",command=self._validar_modelo).pack(side="left",padx=(0,8))
        tk.Button(btn_frame,text="💾 Salvar Template",font=("Segoe UI",10,"bold"),bg=GREEN,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=self._salvar_template).pack(side="left")
        self.var_validacao=tk.StringVar(value="")
        tk.Label(btn_frame,textvariable=self.var_validacao,font=("Segoe UI",9),bg=BG,fg=OK).pack(side="left",padx=12)

        saved=tk.Frame(f,bg=PANEL); saved.pack(fill="both",expand=True,padx=14,pady=(12,12))
        tk.Label(saved,text="TEMPLATES SALVOS",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).pack(anchor="w",padx=12,pady=(10,4))
        self.lista_templates=tk.Listbox(saved,font=("Consolas",9),bg=DARK,fg=TEXT,
                                         selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0,height=6)
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

    def _validar_modelo(self):
        if not self.keywords_atual:
            messagebox.showwarning("","Adicione palavras-chave antes de validar."); return
        caminho=filedialog.askopenfilename(title="PDF modelo",filetypes=[("PDF","*.pdf")])
        if not caminho: return
        ext=self.pdf_svc.extract_from_file(caminho)
        tl=ext.raw_text.lower()
        enc=[kw for kw in self.keywords_atual if kw.lower() in tl]
        falt=[kw for kw in self.keywords_atual if kw.lower() not in tl]
        if not falt:
            self.var_validacao.set(f"✅ Válido — {len(enc)} regra(s) encontradas")
        else:
            self.var_validacao.set(f"⚠ {len(falt)} não encontrada(s)")
            messagebox.showwarning("Falhou","Não encontradas:\n\n"+"\n".join(f"  • {k}" for k in falt))

    def _salvar_template(self):
        nome=self.var_tpl_nome.get().strip(); criador=self.var_tpl_criador.get().strip()
        if not nome: messagebox.showwarning("","Informe o nome."); return
        if not criador: messagebox.showwarning("","Informe quem está criando."); return
        if not self.keywords_atual: messagebox.showwarning("","Adicione palavras-chave."); return
        t=TaskTemplate(id=str(uuid.uuid4())[:8],name=nome,
                        department=Department(self.var_tpl_depto.get()),
                        keywords=list(self.keywords_atual),created_by=criador)
        self.repo.save_template(t)
        self.var_tpl_nome.set(""); self.var_tpl_criador.set("")
        self.keywords_atual=[]; self._render_keywords(); self.var_validacao.set("")
        self._refresh_templates()
        messagebox.showinfo("Salvo!",f"Template '{nome}' salvo com {len(t.keywords)} regra(s).")

    def _refresh_templates(self):
        self.lista_templates.delete(0,"end")
        for t in self.repo.list_templates():
            self.lista_templates.insert("end",
                f"  ○  [{t.department.value}]  {t.name}  —  {len(t.keywords)} regra(s)  (ID: {t.id})")

    def _remover_template(self):
        sel=self.lista_templates.curselection()
        if not sel: return
        t=self.repo.list_templates()[sel[0]]
        if messagebox.askyesno("Remover",f"Remover '{t.name}'?"):
            self.repo.delete_template(t.id); self._refresh_templates()

    # ══════════════════════════════════════════════════════════════════
    # ABA 3 — UPLOAD & ENVIO
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_upload(self):
        f=self.frame_upload
        tk.Button(f,text="+ Selecionar PDF(s)",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=18,pady=8,cursor="hand2",command=self._selecionar_pdfs).pack(pady=(14,0))

        fl=tk.Frame(f,bg=PANEL); fl.pack(fill="x",padx=14,pady=(10,0))
        tk.Label(fl,text="Documentos adicionados:",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,2))
        self.lista_docs=tk.Listbox(fl,height=4,font=("Consolas",9),bg=DARK,fg=TEXT,
                                    selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0)
        self.lista_docs.pack(fill="x",padx=10,pady=(0,4))
        tk.Button(fl,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=self._remover_doc
                  ).pack(anchor="e",padx=10,pady=(0,8))

        fi=tk.Frame(f,bg=PANEL); fi.pack(fill="x",padx=14,pady=(6,0))
        for row,lbl,var_name,cor in [
            (0,"Empresa:",   "var_empresa",  OK),
            (0,"Via:",       "var_id_tipo",  WARN),
            (1,"Depto:",     "var_depto_info",WARN),
            (1,"Destinatários:","var_dest_info",OK),
        ]:
            tk.Label(fi,text=lbl,font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                     ).grid(row=row,column=list("0123456789").index(str([0,0,1,1].index(row)*2+[0,2,0,2][[0,0,1,1].index(row)*2+[0,2,0,2].index(max([0,0,1,1].count(row)-1,0)) if [0,2,0,2].count(max([0,0,1,1].count(row)-1,0)) else 0]))
                             if False else ([0,2,0,2][[0,0,1,1,0,0,1,1].index(row)] if False else {"Empresa:":0,"Via:":2,"Depto:":0,"Destinatários:":2}[lbl]),
                     sticky="w",padx=10,pady=(8,2) if row==0 else 4)
            setattr(self,var_name,tk.StringVar(value="—"))
            tk.Label(fi,textvariable=getattr(self,var_name),font=("Segoe UI",9),bg=PANEL,fg=cor
                     ).grid(row=row,column={"Empresa:":1,"Via:":3,"Depto:":1,"Destinatários:":3}[lbl],
                            sticky="w",padx=6,pady=(8,2) if row==0 else 4)

        tk.Label(fi,text="Competência:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=2,column=0,sticky="w",padx=10,pady=4)
        self.var_competencia=tk.StringVar()
        tk.Entry(fi,textvariable=self.var_competencia,font=("Segoe UI",10),
                 bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=20
                 ).grid(row=2,column=1,sticky="w",padx=6,pady=4)

        flog=tk.Frame(f,bg=PANEL); flog.pack(fill="both",expand=True,padx=14,pady=(10,0))
        tk.Label(flog,text="Log:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).pack(anchor="w",padx=10,pady=(8,2))
        self.log_text=tk.Text(flog,height=8,font=("Consolas",9),bg=DARK,fg=TEXT,
                               relief="flat",bd=0,highlightthickness=0,state="disabled",wrap="word")
        self.log_text.pack(fill="both",expand=True,padx=10,pady=(0,10))
        for tag,cor in [("ok",OK),("warn",WARN),("err",ERR),("info","#89b4fa"),("bold",None)]:
            self.log_text.tag_config(tag,foreground=cor) if cor else self.log_text.tag_config(tag,font=("Consolas",9,"bold"))

        self.btn_enviar=tk.Button(f,text="🚀 Enviar",font=("Segoe UI",11,"bold"),bg=GREEN,fg="white",
                                   relief="flat",padx=20,pady=9,cursor="hand2",
                                   command=self._confirmar_e_enviar,state="disabled")
        self.btn_enviar.pack(pady=10)

    def _selecionar_pdfs(self):
        caminhos=filedialog.askopenfilenames(title="Selecione os PDFs",filetypes=[("PDF","*.pdf")])
        for c in caminhos: self._processar_pdf(c)
        self.btn_enviar.config(state="normal" if self.documentos else "disabled")

    def _processar_pdf(self,caminho):
        filename=os.path.basename(caminho)
        self._log(f"\n{'─'*50}","info"); self._log(f"📄 {filename}","bold")
        clientes=self.repo.list_clients()
        extracao=self.pdf_svc.extract_from_file(caminho,clients=clientes)
        template=self.repo.match_template(extracao.raw_text)

        self._log(f"   Confiança   : {extracao.confidence:.0%}","ok" if extracao.confidence>=0.6 else "warn")
        self._log(f"   Competência : {extracao.suggested_competence or '❓'}",
                  "ok" if extracao.suggested_competence else "warn")

        client_det=None
        if extracao.client_match and extracao.client_match.client:
            client_det=extracao.client_match.client
            metodo="CNPJ" if extracao.client_match.matched_by=="cnpj" else "IE"
            self._log(f"   Empresa     : {client_det.company_name}  [Cód. {client_det.codigo}]  ✅","ok")
            self._log(f"   Via         : {metodo} — {extracao.client_match.matched_value}","ok")
        else:
            self._log("   Empresa     : ❓ Não identificada — seleção manual necessária","err")

        if template:
            self._log(f"   Template    : '{template.name}' [{template.department.value}]","ok")
            # Mostra destinatários já calculados
            if client_det:
                emails=client_det.get_emails_for_department(template.department.value)
                if emails:
                    self._log(f"   Destinatários: {', '.join(emails)}","ok")
                else:
                    self._log(f"   ⚠ Nenhum e-mail cadastrado para {template.department.value} nesta empresa","warn")
        else:
            self._log("   Template    : ⚠ Nenhum vinculado","warn")

        comp_final,client_final=self._janela_confirmacao(filename,extracao,template,client_det)
        if comp_final is None:
            self._log("   ↩ Ignorado.","warn"); return

        doc=DocumentoDetectado(caminho,extracao,comp_final,template,client_final)
        self.documentos.append(doc)
        lbl=f" [{template.name}]" if template else ""
        self.lista_docs.insert("end",f"  ✓  {filename}{lbl}")

        if client_final and self.var_empresa.get()=="—":
            self.var_empresa.set(f"{client_final.company_name} [Cód. {client_final.codigo}]")
            metodo="CNPJ" if (extracao.client_match and extracao.client_match.matched_by=="cnpj") else "IE"
            self.var_id_tipo.set(metodo)

        if template:
            self.var_depto_info.set(template.department.value)
            if client_final:
                emails=client_final.get_emails_for_department(template.department.value)
                self.var_dest_info.set(", ".join(emails) if emails else "⚠ nenhum e-mail configurado")

        if extracao.suggested_competence and not self.var_competencia.get():
            self.var_competencia.set(extracao.suggested_competence)

        self._log(f"   ✅ Adicionado — competência: {comp_final}","ok")

    def _janela_confirmacao(self,filename,extracao,template,client_det):
        popup=tk.Toplevel(self.root); popup.title("Confirmar dados")
        popup.geometry("520x420"); popup.configure(bg=BG); popup.grab_set()
        resultado={"comp":None,"client":client_det}

        tk.Label(popup,text="Confirme os dados detectados",font=("Segoe UI",11,"bold"),bg=BG,fg=TEXT).pack(pady=(14,2))
        tk.Label(popup,text=filename,font=("Consolas",9),bg=BG,fg=SUB).pack()

        if template:
            tk.Label(popup,text=f"✅ Template: {template.name}  [{template.department.value}]",
                     font=("Segoe UI",9,"bold"),bg=BG,fg=OK).pack(pady=(4,0))
        else:
            tk.Label(popup,text="⚠ Nenhum template vinculado",font=("Segoe UI",9),bg=BG,fg=WARN).pack(pady=(4,0))

        frame=tk.Frame(popup,bg=PANEL); frame.pack(fill="x",padx=18,pady=10)

        tk.Label(frame,text="Competência:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=0,column=0,sticky="w",padx=12,pady=(12,4))
        var_comp=tk.StringVar(value=extracao.suggested_competence or "")
        tk.Entry(frame,textvariable=var_comp,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=22).grid(row=0,column=1,padx=12,pady=(12,4))

        tk.Label(frame,text="Cliente:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB
                 ).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        clientes=self.repo.list_clients()
        opcoes=["— Selecionar —"]+[f"[{c.codigo}] {c.company_name}" for c in clientes]

        if client_det:
            metodo="CNPJ" if (extracao.client_match and extracao.client_match.matched_by=="cnpj") else "IE"
            tk.Label(frame,text=f"✅ [{client_det.codigo}] {client_det.company_name} (via {metodo})",
                     font=("Segoe UI",9),bg=PANEL,fg=OK).grid(row=1,column=1,sticky="w",padx=12,pady=4)
            def trocar():
                self._janela_troca_cliente(clientes,resultado,popup)
            tk.Button(frame,text="Trocar",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                      relief="flat",cursor="hand2",command=trocar).grid(row=1,column=2,padx=4)
        else:
            var_c=tk.StringVar(value=opcoes[0])
            ttk.Combobox(frame,textvariable=var_c,values=opcoes,state="readonly",width=36
                         ).grid(row=1,column=1,columnspan=2,padx=12,pady=4)
            tk.Label(frame,text="⚠ Selecione o cliente",font=("Segoe UI",8),
                     bg=PANEL,fg=WARN).grid(row=2,column=1,sticky="w",padx=12)
            def on_c(*_):
                sel=var_c.get()
                if not sel.startswith("—"):
                    resultado["client"]=clientes[opcoes.index(sel)-1]
            var_c.trace_add("write",on_c)

        # Mostra destinatários se tiver template + cliente
        if template and client_det:
            emails=client_det.get_emails_for_department(template.department.value)
            cor=OK if emails else WARN
            txt=f"Destinatários ({template.department.value}): {', '.join(emails)}" if emails else f"⚠ Nenhum e-mail configurado para {template.department.value}"
            tk.Label(popup,text=txt,font=("Segoe UI",8),bg=BG,fg=cor,wraplength=480).pack(pady=(4,0))

        tk.Label(popup,text=f"Confiança: {extracao.confidence:.0%}",font=("Segoe UI",9),
                 bg=BG,fg=OK if extracao.confidence>=0.6 else WARN).pack(pady=(6,0))

        frame_btn=tk.Frame(popup,bg=BG); frame_btn.pack(pady=12)
        def confirmar():
            resultado["comp"]=var_comp.get() or "Não informada"; popup.destroy()
        tk.Button(frame_btn,text="✓ Confirmar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=confirmar).pack(side="left",padx=8)
        tk.Button(frame_btn,text="Ignorar PDF",font=("Segoe UI",10),bg=BTN2,fg=SUB,
                  relief="flat",padx=16,pady=6,cursor="hand2",command=popup.destroy).pack(side="left",padx=8)
        popup.wait_window()
        return resultado["comp"],resultado["client"]

    def _janela_troca_cliente(self,clientes,resultado,parent):
        popup=tk.Toplevel(parent); popup.title("Trocar cliente")
        popup.geometry("460x200"); popup.configure(bg=BG); popup.grab_set()
        tk.Label(popup,text="Selecione o cliente correto:",font=("Segoe UI",10,"bold"),bg=BG,fg=TEXT).pack(pady=(16,8))
        opcoes=["— Nenhum —"]+[f"[{c.codigo}] {c.company_name}" for c in clientes]
        var=tk.StringVar(value=opcoes[0])
        ttk.Combobox(popup,textvariable=var,values=opcoes,state="readonly",width=48).pack(padx=18)
        def confirmar():
            sel=var.get()
            if not sel.startswith("—"): resultado["client"]=clientes[opcoes.index(sel)-1]
            popup.destroy()
        tk.Button(popup,text="Confirmar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=confirmar).pack(pady=14)
        popup.wait_window()

    def _remover_doc(self):
        sel=self.lista_docs.curselection()
        if not sel: return
        doc=self.documentos.pop(sel[0]); self.lista_docs.delete(sel[0])
        self._log(f"   🗑 Removido: {doc.filename}","warn")
        self.btn_enviar.config(state="normal" if self.documentos else "disabled")

    # ── ENVIO AUTOMÁTICO POR DEPARTAMENTO ─────────────────────────────

    def _confirmar_e_enviar(self):
        if not self.documentos:
            messagebox.showwarning("","Adicione PDFs antes de enviar."); return

        # Agrupa por cliente + departamento para calcular destinatários
        resumo_envios=[]
        for doc in self.documentos:
            client=doc.client
            dept=doc.template.department.value if doc.template else None
            if client and dept:
                emails=client.get_emails_for_department(dept)
                resumo_envios.append(f"  [{dept}] {client.company_name} → {', '.join(emails) if emails else '⚠ SEM E-MAIL'}")
            else:
                resumo_envios.append(f"  {doc.filename} → ⚠ cliente ou template não definido")

        competencia=self.var_competencia.get() or "Não informada"
        if not messagebox.askyesno("Confirmar envio",
            f"Confirma o envio?\n\nDe: {GMAIL_REMETENTE}\n"
            f"Competência: {competencia}\n\n"
            f"Envios que serão realizados:\n"+"\n".join(resumo_envios)+
            "\n\nOs e-mails serão disparados automaticamente."): return

        self._log(f"\n{'═'*50}","info"); self._log("🚀 INICIANDO ENVIOS...","bold")

        for doc in self.documentos:
            client=doc.client
            dept=doc.template.department.value if doc.template else None
            if not client or not dept:
                self._log(f"   ⚠ Pulando {doc.filename} — cliente ou template não definido","warn"); continue
            emails=client.get_emails_for_department(dept)
            if not emails:
                self._log(f"   ⚠ {client.company_name} [{dept}] — nenhum e-mail configurado","warn"); continue
            try:
                self._enviar_documento(doc, emails, competencia)
                self._log(f"   ✅ {doc.filename} → {', '.join(emails)}","ok")
            except Exception as e:
                self._log(f"   ❌ {doc.filename} — ERRO: {e}","err")

        self._log("🏁 Envios concluídos.","bold")
        messagebox.showinfo("Concluído","Todos os envios foram processados.\nVerifique o log para detalhes.")

    def _enviar_documento(self, doc, destinatarios: list[str], competencia: str):
        client=doc.client
        dept=doc.template.department.value if doc.template else "GERAL"
        nome_tarefa=doc.template.name if doc.template else doc.filename

        msg=MIMEMultipart()
        msg["From"]=GMAIL_REMETENTE
        msg["To"]=", ".join(destinatarios)
        msg["Subject"]=f"[{dept}] {nome_tarefa} — {client.company_name} — {competencia}"

        corpo=(
            f"Prezado(a),\n\n"
            f"Segue em anexo o documento referente à competência {competencia}.\n\n"
            f"Empresa  : {client.company_name}\n"
            f"CNPJ     : {client.mask_cnpj()}\n"
            f"Depto    : {dept}\n"
            f"Documento: {doc.filename}\n\n"
            f"Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n"
        )
        msg.attach(MIMEText(corpo,"plain","utf-8"))

        with open(doc.caminho,"rb") as f:
            parte=MIMEApplication(f.read(),_subtype="pdf")
            parte.add_header("Content-Disposition","attachment",filename=doc.filename)
            msg.attach(parte)

        with smtplib.SMTP("smtp.gmail.com",587) as s:
            s.ehlo(); s.starttls()
            s.login(GMAIL_REMETENTE,GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_REMETENTE,destinatarios,msg.as_string())

    def _log(self,msg,tag=""):
        self.log_text.config(state="normal")
        line=f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n" if msg.strip() else "\n"
        self.log_text.insert("end",line,tag); self.log_text.see("end")
        self.log_text.config(state="disabled"); self.root.update_idletasks()


# ── MAIN ──────────────────────────────────────────────────────────────
if __name__=="__main__":
    erros=[]
    if "seuemail" in GMAIL_REMETENTE: erros.append("• Preencha GMAIL_REMETENTE")
    if "xxxx" in GMAIL_APP_PASSWORD:  erros.append("• Preencha GMAIL_APP_PASSWORD")
    if erros:
        print("\n⚠ Configure antes de rodar:\n")
        for e in erros: print(f"  {e}")
        sys.exit(1)
    root=tk.Tk(); DemoApp(root); root.mainloop()

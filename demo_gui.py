"""
DEMO GUI — Sistema de Guias
Aba 1: Empresas
Aba 2: Templates
Aba 3: Upload & Envio
Aba 4: Histórico
"""
import os, sys, uuid, shutil, smtplib, tkinter as tk
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
from app.models.email_log import EmailLog, EmailStatus
from app.repositories.mock_repository import MockRepository

# ══════════════════════════════════════════════════════════════════════
GMAIL_REMETENTE    = "seuemail@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
HISTORICO_DIR      = os.path.join(os.path.dirname(__file__), "historico", "pdfs")
# ══════════════════════════════════════════════════════════════════════

BG=("#1e1e2e"); PANEL=("#2a2a3e"); ACCENT=("#7c6af7"); TEXT=("#cdd6f4")
SUB=("#a6adc8"); OK=("#a6e3a1"); WARN=("#f9e2af"); ERR=("#f38ba8")
DARK=("#13131f"); BTN2=("#313244"); GREEN=("#40a060")
ALL_DEPTS=[d.value for d in Department]
SENT_BY_DEFAULT = "Sistema"   # substituído pelo login futuramente


class DocumentoDetectado:
    def __init__(self, caminho, extracao, competencia, template=None, client=None):
        self.caminho=caminho; self.filename=os.path.basename(caminho)
        self.size_kb=os.path.getsize(caminho)/1024; self.extracao=extracao
        self.competencia=competencia; self.template=template; self.client=client

    @property
    def pode_enviar(self) -> bool:
        """PDF só pode ser enviado se tiver template vinculado."""
        return self.template is not None

    @property
    def bloqueio_motivo(self) -> str:
        if not self.template:
            return "Nenhuma tarefa encontrada para este PDF"
        return ""


class DemoApp:
    def __init__(self, root):
        self.root=root; self.root.title("Sistema de Guias")
        self.root.geometry("900x760"); self.root.resizable(False,False)
        self.root.configure(bg=BG)
        self.pdf_svc=PDFService(); self.xlsx_svc=XlsxService()
        self.repo=MockRepository()
        self.documentos=[]; self.keywords_atual=[]
        os.makedirs(HISTORICO_DIR, exist_ok=True)
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
        self.frame_empresas  =tk.Frame(nb,bg=BG)
        self.frame_templates =tk.Frame(nb,bg=BG)
        self.frame_upload    =tk.Frame(nb,bg=BG)
        self.frame_historico =tk.Frame(nb,bg=BG)
        nb.add(self.frame_empresas,  text="  🏢 Empresas  ")
        nb.add(self.frame_templates, text="  📋 Templates  ")
        nb.add(self.frame_upload,    text="  📤 Upload & Envio  ")
        nb.add(self.frame_historico, text="  📜 Histórico  ")
        self.nb=nb
        self._build_aba_empresas()
        self._build_aba_templates()
        self._build_aba_upload()
        self._build_aba_historico()

    # ══════════════════════════════════════════════════════════════════
    # ABA 1 — EMPRESAS
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_empresas(self):
        f=self.frame_empresas
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

        bf=tk.Frame(f,bg=PANEL); bf.pack(fill="x",padx=14,pady=(0,6))
        tk.Label(bf,text="🔍",font=("Segoe UI",11),bg=PANEL,fg=SUB).pack(side="left",padx=(10,4),pady=6)
        self.var_busca=tk.StringVar()
        self.var_busca.trace_add("write",lambda *_: self._filtrar())
        tk.Entry(bf,textvariable=self.var_busca,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=44).pack(side="left",pady=6)
        tk.Label(bf,text="Buscar por nome, CNPJ, código ou IE",
                 font=("Segoe UI",8),bg=PANEL,fg=SUB).pack(side="left",padx=10)

        tf=tk.Frame(f,bg=PANEL); tf.pack(fill="both",expand=True,padx=14,pady=(0,4))
        cols=("codigo","tipo","nome","cnpj","ie","emails")
        self.tree=ttk.Treeview(tf,columns=cols,show="headings",height=14)
        for col,lbl,w in zip(cols,["Cód.","Tipo","Nome","CNPJ","IE","E-mails"],[55,55,230,150,130,200]):
            self.tree.heading(col,text=lbl,command=lambda c=col: self._sort(c))
            self.tree.column(col,width=w,minwidth=30)
        vsb=ttk.Scrollbar(tf,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left",fill="both",expand=True)
        vsb.pack(side="right",fill="y")
        self.tree.bind("<<TreeviewSelect>>",self._on_select)
        self.tree.bind("<Double-1>",lambda e: self._abrir_gerenciar_emails())

        dp=tk.Frame(f,bg=PANEL); dp.pack(fill="x",padx=14,pady=(0,4))
        tk.Label(dp,text="E-mails da empresa selecionada:",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(6,2))
        self.var_emails_detalhe=tk.StringVar(value="Selecione uma empresa")
        tk.Label(dp,textvariable=self.var_emails_detalhe,font=("Consolas",8),
                 bg=PANEL,fg=OK,justify="left",wraplength=860).pack(anchor="w",padx=14,pady=(0,6))

        self.var_sync=tk.StringVar(value="")
        tk.Label(f,textvariable=self.var_sync,font=("Segoe UI",8),bg=BG,fg=WARN,wraplength=860).pack(anchor="w",padx=14,pady=(0,4))

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
        emails_backup={c.cnpj_digits(): c.emails for c in self.repo.list_clients(active_only=False)}
        result=self.xlsx_svc.sync(path,self.repo)
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

    def _atualizar_tabela(self): self._filtrar()

    def _filtrar(self):
        q=self.var_busca.get().lower() if hasattr(self,"var_busca") else ""
        for item in self.tree.get_children(): self.tree.delete(item)
        clientes=self.repo.list_clients(active_only=False)
        filtrados=[c for c in clientes if
                   q in (c.company_name or "").lower() or q in (c.cnpj_digits() or "") or
                   q in (c.codigo or "").lower() or q in (c.ie_digits() or "")] if q else clientes
        for c in filtrados:
            tipo="CPF" if len(c.cnpj_digits())==11 else "CNPJ"
            n=len(c.emails)
            self.tree.insert("","end",iid=c.id,values=(
                c.codigo or "—", tipo, c.company_name, c.mask_cnpj(),
                c.inscricao_estadual or "—",
                f"{n} e-mail(s)" if n else "— sem e-mails"))
        total=len(clientes)
        self.var_total.set(f"{total} empresa(s)"+(f"  |  {len(filtrados)} exibida(s)" if q else ""))

    def _on_select(self,event):
        sel=self.tree.selection()
        if not sel: return
        c=self.repo.get_client(sel[0])
        if not c: return
        if not c.emails:
            self.var_emails_detalhe.set("Nenhum e-mail cadastrado. Clique em 'Gerenciar E-mails'."); return
        linhas=[]
        for ce in c.emails:
            deptos=", ".join(ce.departments) if ce.departments else "nenhum depto"
            linhas.append(f"  {ce.email}  [{ce.label}]  →  {deptos}")
        self.var_emails_detalhe.set("\n".join(linhas))

    def _sort(self,col):
        items=[(self.tree.set(k,col),k) for k in self.tree.get_children("")]
        items.sort(key=lambda x: x[0].lower())
        for i,(_,k) in enumerate(items): self.tree.move(k,"",i)

    def _abrir_gerenciar_emails(self):
        sel=self.tree.selection()
        if not sel:
            messagebox.showinfo("","Selecione uma empresa na tabela primeiro."); return
        client=self.repo.get_client(sel[0])
        if not client: return
        self._janela_emails(client)

    def _janela_emails(self,client):
        win=tk.Toplevel(self.root)
        win.title(f"E-mails — {client.company_name}")
        win.geometry("680x580"); win.configure(bg=BG); win.grab_set()

        tk.Label(win,text="✉ Gerenciar E-mails",font=("Segoe UI",12,"bold"),bg=BG,fg=TEXT).pack(pady=(14,2))
        tk.Label(win,text=f"{client.company_name}  |  {client.mask_cnpj()}  |  Cód. {client.codigo}",
                 font=("Segoe UI",9),bg=BG,fg=SUB).pack(pady=(0,10))

        tf=tk.Frame(win,bg=PANEL); tf.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(tf,text="E-MAILS CADASTRADOS",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,4))
        cols=("email","label","deptos")
        etree=ttk.Treeview(tf,columns=cols,show="headings",height=6)
        for col,lbl,w in zip(cols,["E-mail","Rótulo","Departamentos"],[220,120,270]):
            etree.heading(col,text=lbl); etree.column(col,width=w,minwidth=40)
        etree.pack(fill="x",padx=10,pady=(0,4))

        def refresh():
            for i in etree.get_children(): etree.delete(i)
            for ce in client.emails:
                etree.insert("","end",values=(ce.email,ce.label,", ".join(ce.departments) if ce.departments else "— nenhum"))

        refresh()

        def remover():
            sel_e=etree.selection()
            if not sel_e: return
            email_sel=etree.item(sel_e[0])["values"][0]
            if messagebox.askyesno("Remover",f"Remover '{email_sel}'?"):
                client.remove_email(email_sel); self.repo.save_client(client)
                refresh(); self._atualizar_tabela(); self._on_select(None)

        tk.Button(tf,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=remover
                  ).pack(anchor="e",padx=10,pady=(0,8))

        form=tk.Frame(win,bg=PANEL); form.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(form,text="ADICIONAR E-MAIL",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).grid(row=0,column=0,columnspan=4,sticky="w",padx=12,pady=(10,6))
        tk.Label(form,text="E-mail*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=1,column=0,sticky="w",padx=12,pady=4)
        var_email=tk.StringVar()
        tk.Entry(form,textvariable=var_email,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=28).grid(row=1,column=1,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Rótulo*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=1,column=2,sticky="w",padx=12,pady=4)
        var_label=tk.StringVar()
        tk.Entry(form,textvariable=var_label,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=16).grid(row=1,column=3,sticky="w",padx=6,pady=4)
        tk.Label(form,text="Departamentos*",font=("Segoe UI",9),bg=PANEL,fg=TEXT
                 ).grid(row=2,column=0,sticky="nw",padx=12,pady=(6,4))
        df=tk.Frame(form,bg=PANEL); df.grid(row=2,column=1,columnspan=3,sticky="w",padx=6,pady=(6,4))
        dept_vars={d: tk.BooleanVar() for d in ALL_DEPTS}
        for i,d in enumerate(ALL_DEPTS):
            tk.Checkbutton(df,text=d,variable=dept_vars[d],font=("Segoe UI",9),bg=PANEL,fg=TEXT,
                           selectcolor=DARK,activebackground=PANEL,cursor="hand2"
                           ).grid(row=i//3,column=i%3,sticky="w",padx=6,pady=2)

        def adicionar():
            email=var_email.get().strip().lower(); label=var_label.get().strip()
            deptos=[d for d,v in dept_vars.items() if v.get()]
            if not email: messagebox.showwarning("","Informe o e-mail."); return
            if not label: messagebox.showwarning("","Informe o rótulo."); return
            if not deptos: messagebox.showwarning("","Selecione ao menos um departamento."); return
            if "@" not in email: messagebox.showwarning("","E-mail inválido."); return
            if any(ce.email==email for ce in client.emails):
                messagebox.showwarning("Duplicado",f"'{email}' já cadastrado."); return
            client.add_email(email,label,deptos); self.repo.save_client(client)
            var_email.set(""); var_label.set("")
            for v in dept_vars.values(): v.set(False)
            refresh(); self._atualizar_tabela(); self._on_select(None)

        tk.Button(form,text="+ Adicionar E-mail",font=("Segoe UI",10,"bold"),
                  bg=GREEN,fg="white",relief="flat",padx=14,pady=6,cursor="hand2",
                  command=adicionar).grid(row=3,column=0,columnspan=4,pady=(8,12),padx=12,sticky="w")

        resumo=tk.Frame(win,bg=PANEL); resumo.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(resumo,text="RESUMO POR DEPARTAMENTO",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,4))

        def render_resumo():
            for w in resumo.winfo_children():
                if hasattr(w,'_resumo'): w.destroy()
            linhas=[f"  {d:<12} → {', '.join(client.get_emails_for_department(d))}"
                    for d in ALL_DEPTS if client.get_emails_for_department(d)]
            lbl=tk.Label(resumo,
                         text="\n".join(linhas) if linhas else "  Nenhum e-mail configurado ainda.",
                         font=("Consolas",8),bg=PANEL,fg=OK if linhas else WARN,justify="left")
            lbl._resumo=True; lbl.pack(anchor="w",padx=14,pady=(0,8))

        render_resumo()
        tk.Button(win,text="✓ Fechar",font=("Segoe UI",10,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=18,pady=7,cursor="hand2",
                  command=lambda: [win.destroy(), self._atualizar_tabela(), self._on_select(None)]
                  ).pack(pady=4)

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

        kw=tk.Frame(f,bg=PANEL); kw.pack(fill="x",padx=14,pady=(10,0))
        tk.Label(kw,text="PALAVRAS-CHAVE  (PDF deve conter TODAS)",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(10,2))
        tk.Label(kw,text="Use termos fixos. Evite CNPJ, IE, nomes e datas variáveis.",font=("Segoe UI",8),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(0,6))
        rkw=tk.Frame(kw,bg=PANEL); rkw.pack(fill="x",padx=12,pady=(0,6))
        self.var_kw_input=tk.StringVar()
        self.entry_kw=tk.Entry(rkw,textvariable=self.var_kw_input,font=("Segoe UI",10),
                                bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=38)
        self.entry_kw.pack(side="left")
        self.entry_kw.bind("<Return>",lambda e: self._add_keyword())
        tk.Button(rkw,text="+ Adicionar",font=("Segoe UI",9,"bold"),bg=ACCENT,fg="white",
                  relief="flat",padx=12,pady=4,cursor="hand2",command=self._add_keyword).pack(side="left",padx=(8,0))
        self.frame_kw_lista=tk.Frame(kw,bg=PANEL); self.frame_kw_lista.pack(fill="x",padx=12,pady=(0,10))

        bf=tk.Frame(f,bg=BG); bf.pack(fill="x",padx=14,pady=(8,0))
        tk.Button(bf,text="📄 Validar com PDF modelo",font=("Segoe UI",9),bg=BTN2,fg=TEXT,
                  relief="flat",padx=14,pady=6,cursor="hand2",command=self._validar_modelo).pack(side="left",padx=(0,8))
        tk.Button(bf,text="💾 Salvar Template",font=("Segoe UI",10,"bold"),bg=GREEN,fg="white",
                  relief="flat",padx=16,pady=6,cursor="hand2",command=self._salvar_template).pack(side="left")
        self.var_validacao=tk.StringVar(value="")
        tk.Label(bf,textvariable=self.var_validacao,font=("Segoe UI",9),bg=BG,fg=OK).pack(side="left",padx=12)

        sv=tk.Frame(f,bg=PANEL); sv.pack(fill="both",expand=True,padx=14,pady=(12,12))
        tk.Label(sv,text="TEMPLATES SALVOS",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=12,pady=(10,4))
        self.lista_templates=tk.Listbox(sv,font=("Consolas",9),bg=DARK,fg=TEXT,
                                         selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0,height=6)
        self.lista_templates.pack(fill="both",expand=True,padx=12,pady=(0,4))
        tk.Button(sv,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=self._remover_template
                  ).pack(anchor="e",padx=12,pady=(0,8))

    def _add_keyword(self):
        kw=self.var_kw_input.get().strip()
        if not kw: return
        if kw.lower() in [k.lower() for k in self.keywords_atual]:
            messagebox.showwarning("Duplicada",f"'{kw}' já adicionada."); return
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
        if not self.keywords_atual: messagebox.showwarning("","Adicione palavras-chave antes de validar."); return
        caminho=filedialog.askopenfilename(title="PDF modelo",filetypes=[("PDF","*.pdf")])
        if not caminho: return
        ext=self.pdf_svc.extract_from_file(caminho); tl=ext.raw_text.lower()
        enc=[kw for kw in self.keywords_atual if kw.lower() in tl]
        falt=[kw for kw in self.keywords_atual if kw.lower() not in tl]
        if not falt: self.var_validacao.set(f"✅ Válido — {len(enc)} regra(s) encontradas")
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
        messagebox.showinfo("Salvo!",f"Template '{nome}' salvo.")

    def _refresh_templates(self):
        self.lista_templates.delete(0,"end")
        for t in self.repo.list_templates():
            self.lista_templates.insert("end",f"  ○  [{t.department.value}]  {t.name}  —  {len(t.keywords)} regra(s)  (ID: {t.id})")

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
        tk.Label(fl,text="Documentos adicionados:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,2))
        self.lista_docs=tk.Listbox(fl,height=5,font=("Consolas",9),bg=DARK,fg=TEXT,
                                    selectbackground=ACCENT,relief="flat",bd=0,highlightthickness=0)
        self.lista_docs.pack(fill="x",padx=10,pady=(0,4))
        tk.Button(fl,text="🗑 Remover selecionado",font=("Segoe UI",8),bg=BTN2,fg=SUB,
                  relief="flat",cursor="hand2",pady=4,command=self._remover_doc
                  ).pack(anchor="e",padx=10,pady=(0,8))

        fi=tk.Frame(f,bg=PANEL); fi.pack(fill="x",padx=14,pady=(6,0))
        tk.Label(fi,text="Empresa:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).grid(row=0,column=0,sticky="w",padx=10,pady=(8,2))
        self.var_empresa=tk.StringVar(value="—")
        tk.Label(fi,textvariable=self.var_empresa,font=("Segoe UI",9),bg=PANEL,fg=OK).grid(row=0,column=1,sticky="w",padx=6,pady=(8,2))
        tk.Label(fi,text="Via:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).grid(row=0,column=2,sticky="w",padx=10,pady=(8,2))
        self.var_id_tipo=tk.StringVar(value="—")
        tk.Label(fi,textvariable=self.var_id_tipo,font=("Segoe UI",9),bg=PANEL,fg=WARN).grid(row=0,column=3,sticky="w",padx=6,pady=(8,2))
        tk.Label(fi,text="Depto:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).grid(row=1,column=0,sticky="w",padx=10,pady=4)
        self.var_depto_info=tk.StringVar(value="—")
        tk.Label(fi,textvariable=self.var_depto_info,font=("Segoe UI",9),bg=PANEL,fg=WARN).grid(row=1,column=1,sticky="w",padx=6,pady=4)
        tk.Label(fi,text="Destinatários:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).grid(row=1,column=2,sticky="w",padx=10,pady=4)
        self.var_dest_info=tk.StringVar(value="—")
        tk.Label(fi,textvariable=self.var_dest_info,font=("Segoe UI",9),bg=PANEL,fg=OK,wraplength=300).grid(row=1,column=3,sticky="w",padx=6,pady=4)
        tk.Label(fi,text="Competência:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).grid(row=2,column=0,sticky="w",padx=10,pady=4)
        self.var_competencia=tk.StringVar()
        tk.Entry(fi,textvariable=self.var_competencia,font=("Segoe UI",10),
                 bg=DARK,fg=TEXT,insertbackground=TEXT,relief="flat",width=20).grid(row=2,column=1,sticky="w",padx=6,pady=4)

        flog=tk.Frame(f,bg=PANEL); flog.pack(fill="both",expand=True,padx=14,pady=(10,0))
        tk.Label(flog,text="Log:",font=("Segoe UI",9,"bold"),bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(8,2))
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
        self.btn_enviar.config(state="normal" if any(d.pode_enviar for d in self.documentos) else "disabled")

    def _processar_pdf(self,caminho):
        filename=os.path.basename(caminho)
        self._log(f"\n{'─'*50}","info"); self._log(f"📄 {filename}","bold")
        clientes=self.repo.list_clients()
        extracao=self.pdf_svc.extract_from_file(caminho,clients=clientes)
        template=self.repo.match_template(extracao.raw_text)

        self._log(f"   Confiança   : {extracao.confidence:.0%}","ok" if extracao.confidence>=0.6 else "warn")
        self._log(f"   Competência : {extracao.suggested_competence or '❓'}","ok" if extracao.suggested_competence else "warn")

        client_det=None
        if extracao.client_match and extracao.client_match.client:
            client_det=extracao.client_match.client
            metodo="CNPJ" if extracao.client_match.matched_by=="cnpj" else "IE"
            self._log(f"   Empresa     : {client_det.company_name}  [Cód. {client_det.codigo}]  ✅","ok")
            self._log(f"   Via         : {metodo}","ok")
        else:
            self._log("   Empresa     : ❓ Não identificada","warn")

        if template:
            self._log(f"   Template    : '{template.name}' [{template.department.value}]  ✅","ok")
            if client_det:
                emails=client_det.get_emails_for_department(template.department.value)
                self._log(f"   Destinatários: {', '.join(emails) if emails else '⚠ nenhum e-mail configurado'}",
                          "ok" if emails else "warn")
        else:
            self._log(f"   ❌ BLOQUEADO: Nenhuma tarefa encontrada para este PDF — envio não permitido","err")

        comp_final,client_final=self._janela_confirmacao(filename,extracao,template,client_det)
        if comp_final is None:
            self._log("   ↩ Ignorado.","warn"); return

        doc=DocumentoDetectado(caminho,extracao,comp_final,template,client_final)
        self.documentos.append(doc)

        if not doc.pode_enviar:
            self.lista_docs.insert("end",f"  ✗  ⚠ SEM TAREFA  {filename}")
        else:
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
                self.var_dest_info.set(", ".join(emails) if emails else "⚠ nenhum configurado")
        if extracao.suggested_competence and not self.var_competencia.get():
            self.var_competencia.set(extracao.suggested_competence)

        self.btn_enviar.config(state="normal" if any(d.pode_enviar for d in self.documentos) else "disabled")

    def _janela_confirmacao(self,filename,extracao,template,client_det):
        popup=tk.Toplevel(self.root); popup.title("Confirmar dados")
        popup.geometry("540x400"); popup.configure(bg=BG); popup.grab_set()
        resultado={"comp":None,"client":client_det}

        tk.Label(popup,text="Confirme os dados detectados",font=("Segoe UI",11,"bold"),bg=BG,fg=TEXT).pack(pady=(14,2))
        tk.Label(popup,text=filename,font=("Consolas",9),bg=BG,fg=SUB).pack()

        if template:
            tk.Label(popup,text=f"✅ Tarefa: {template.name}  [{template.department.value}]",
                     font=("Segoe UI",9,"bold"),bg=BG,fg=OK).pack(pady=(4,0))
        else:
            tk.Label(popup,text="❌ Nenhuma tarefa vinculada — PDF será bloqueado para envio",
                     font=("Segoe UI",9,"bold"),bg=BG,fg=ERR).pack(pady=(4,0))

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
            def on_c(*_):
                sel=var_c.get()
                if not sel.startswith("—"): resultado["client"]=clientes[opcoes.index(sel)-1]
            var_c.trace_add("write",on_c)

        if template and client_det:
            emails=client_det.get_emails_for_department(template.department.value)
            cor=OK if emails else WARN
            txt=f"Destinatários: {', '.join(emails)}" if emails else f"⚠ Nenhum e-mail para {template.department.value}"
            tk.Label(popup,text=txt,font=("Segoe UI",8),bg=BG,fg=cor,wraplength=500).pack(pady=(2,0))

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
        self.btn_enviar.config(state="normal" if any(d.pode_enviar for d in self.documentos) else "disabled")

    # ── ENVIO ─────────────────────────────────────────────────────────

    def _confirmar_e_enviar(self):
        aptos=[d for d in self.documentos if d.pode_enviar]
        bloqueados=[d for d in self.documentos if not d.pode_enviar]
        if not aptos: messagebox.showwarning("","Nenhum PDF apto para envio."); return

        competencia=self.var_competencia.get() or "Não informada"
        resumo=[]
        for doc in aptos:
            dept=doc.template.department.value
            emails=doc.client.get_emails_for_department(dept) if doc.client else []
            resumo.append(f"  [{dept}] {doc.filename}\n    → {', '.join(emails) if emails else '⚠ SEM E-MAIL'}")
        if bloqueados:
            resumo.append(f"\n  ⚠ {len(bloqueados)} PDF(s) sem tarefa serão ignorados:")
            for d in bloqueados: resumo.append(f"    • {d.filename}")

        if not messagebox.askyesno("Confirmar envio",
            f"Competência: {competencia}\n\nEnvios:\n"+"\n".join(resumo)+
            "\n\nConfirma?"): return

        self._log(f"\n{'═'*50}","info"); self._log("🚀 INICIANDO ENVIOS...","bold")
        for doc in bloqueados:
            self._log(f"   ⚠ Ignorado (sem tarefa): {doc.filename}","warn")

        for doc in aptos:
            dept=doc.template.department.value
            emails=doc.client.get_emails_for_department(dept) if doc.client else []
            if not emails:
                self._log(f"   ⚠ {doc.filename} — nenhum e-mail configurado para {dept}","warn")
                self._registrar_log(doc,competencia,[],EmailStatus.FALHOU,"Nenhum e-mail configurado para o departamento")
                continue
            try:
                stored_path=self._salvar_copia_pdf(doc)
                self._enviar_documento(doc,emails,competencia)
                self._registrar_log(doc,competencia,emails,EmailStatus.ENVIADO,stored_path=stored_path)
                self._log(f"   ✅ {doc.filename} → {', '.join(emails)}","ok")
            except Exception as e:
                self._registrar_log(doc,competencia,emails,EmailStatus.FALHOU,error=str(e))
                self._log(f"   ❌ {doc.filename} — ERRO: {e}","err")

        self._log("🏁 Concluído.","bold")
        self._refresh_historico()
        messagebox.showinfo("Concluído","Envios processados.\nConsulte o Histórico para detalhes.")

    def _salvar_copia_pdf(self,doc) -> str:
        """Copia o PDF para historico/pdfs/ com nome único para acesso futuro."""
        ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name=f"{ts}_{doc.filename}"
        dest=os.path.join(HISTORICO_DIR,safe_name)
        shutil.copy2(doc.caminho,dest)
        return dest

    def _enviar_documento(self,doc,destinatarios,competencia):
        client=doc.client; dept=doc.template.department.value; nome_tarefa=doc.template.name
        msg=MIMEMultipart()
        msg["From"]=GMAIL_REMETENTE; msg["To"]=", ".join(destinatarios)
        msg["Subject"]=f"[{dept}] {nome_tarefa} — {client.company_name} — {competencia}"
        corpo=(f"Prezado(a),\n\nSegue em anexo o documento referente à competência {competencia}.\n\n"
               f"Empresa  : {client.company_name}\nCNPJ     : {client.mask_cnpj()}\n"
               f"Depto    : {dept}\nDocumento: {doc.filename}\n\n"
               f"Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n")
        msg.attach(MIMEText(corpo,"plain","utf-8"))
        with open(doc.caminho,"rb") as f:
            p=MIMEApplication(f.read(),_subtype="pdf")
            p.add_header("Content-Disposition","attachment",filename=doc.filename)
            msg.attach(p)
        with smtplib.SMTP("smtp.gmail.com",587) as s:
            s.ehlo(); s.starttls(); s.login(GMAIL_REMETENTE,GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_REMETENTE,destinatarios,msg.as_string())

    def _registrar_log(self,doc,competencia,recipients,status,stored_path="",error=None):
        log=EmailLog(
            id=str(uuid.uuid4())[:8],
            task_name=doc.template.name if doc.template else "—",
            client_id=doc.client.id if doc.client else "—",
            client_name=doc.client.company_name if doc.client else "—",
            document_filename=doc.filename,
            document_stored_path=stored_path,
            recipients=recipients,
            department=doc.template.department.value if doc.template else "—",
            sent_by=SENT_BY_DEFAULT,
            competence=competencia,
            status=status,
            error_message=error,
        )
        self.repo.save_email_log(log)

    # ══════════════════════════════════════════════════════════════════
    # ABA 4 — HISTÓRICO
    # ══════════════════════════════════════════════════════════════════

    def _build_aba_historico(self):
        f=self.frame_historico

        # Toolbar
        tb=tk.Frame(f,bg=BG); tb.pack(fill="x",padx=14,pady=(12,6))
        tk.Label(tb,text="📜 Histórico de Envios",font=("Segoe UI",11,"bold"),bg=BG,fg=TEXT).pack(side="left")
        tk.Button(tb,text="🔄 Atualizar",font=("Segoe UI",9),bg=BTN2,fg=TEXT,
                  relief="flat",padx=10,pady=6,cursor="hand2",
                  command=self._refresh_historico).pack(side="right")
        tk.Button(tb,text="📁 Abrir pasta de PDFs",font=("Segoe UI",9),bg=BTN2,fg=TEXT,
                  relief="flat",padx=10,pady=6,cursor="hand2",
                  command=lambda: os.startfile(HISTORICO_DIR)).pack(side="right",padx=(0,8))

        # Filtros
        ff=tk.Frame(f,bg=PANEL); ff.pack(fill="x",padx=14,pady=(0,6))
        tk.Label(ff,text="🔍",font=("Segoe UI",11),bg=PANEL,fg=SUB).pack(side="left",padx=(10,4),pady=6)
        self.var_hist_busca=tk.StringVar()
        self.var_hist_busca.trace_add("write",lambda *_: self._refresh_historico())
        tk.Entry(ff,textvariable=self.var_hist_busca,font=("Segoe UI",10),bg=DARK,fg=TEXT,
                 insertbackground=TEXT,relief="flat",width=30).pack(side="left",pady=6)
        tk.Label(ff,text="Status:",font=("Segoe UI",9),bg=PANEL,fg=SUB).pack(side="left",padx=(12,4))
        self.var_hist_status=tk.StringVar(value="TODOS")
        ttk.Combobox(ff,textvariable=self.var_hist_status,
                     values=["TODOS","ENVIADO","FALHOU","SIMULADO"],
                     state="readonly",width=10).pack(side="left",pady=6)
        self.var_hist_status.trace_add("write",lambda *_: self._refresh_historico())
        self.var_hist_total=tk.StringVar(value="0 registros")
        tk.Label(ff,textvariable=self.var_hist_total,font=("Segoe UI",9),bg=PANEL,fg=SUB).pack(side="right",padx=12)

        # Tabela principal
        hf=tk.Frame(f,bg=PANEL); hf.pack(fill="both",expand=True,padx=14,pady=(0,4))
        cols=("data","tarefa","empresa","depto","documento","status","enviado_por")
        self.hist_tree=ttk.Treeview(hf,columns=cols,show="headings",height=14)
        for col,lbl,w in zip(cols,
            ["Data/Hora","Tarefa","Empresa","Depto","Documento","Status","Enviado por"],
            [130,160,180,80,170,80,100]):
            self.hist_tree.heading(col,text=lbl)
            self.hist_tree.column(col,width=w,minwidth=30)
        vsb=ttk.Scrollbar(hf,orient="vertical",command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=vsb.set)
        self.hist_tree.pack(side="left",fill="both",expand=True)
        vsb.pack(side="right",fill="y")
        self.hist_tree.bind("<<TreeviewSelect>>",self._on_select_hist)

        # Painel de detalhe do log selecionado
        dp=tk.Frame(f,bg=PANEL); dp.pack(fill="x",padx=14,pady=(0,4))
        tk.Label(dp,text="Detalhes do envio selecionado:",font=("Segoe UI",9,"bold"),
                 bg=PANEL,fg=SUB).pack(anchor="w",padx=10,pady=(6,2))

        self.var_hist_detalhe=tk.StringVar(value="Selecione um registro para ver detalhes")
        tk.Label(dp,textvariable=self.var_hist_detalhe,font=("Consolas",8),
                 bg=PANEL,fg=TEXT,justify="left",wraplength=860).pack(anchor="w",padx=14,pady=(0,2))

        # Botão de download do PDF
        self.btn_download=tk.Button(dp,text="⬇ Baixar PDF",font=("Segoe UI",9,"bold"),
                                     bg=ACCENT,fg="white",relief="flat",padx=12,pady=5,
                                     cursor="hand2",state="disabled",command=self._baixar_pdf_historico)
        self.btn_download.pack(anchor="w",padx=14,pady=(4,8))

        # Tags de cor por status
        self.hist_tree.tag_configure("ENVIADO",  foreground=OK)
        self.hist_tree.tag_configure("FALHOU",   foreground=ERR)
        self.hist_tree.tag_configure("SIMULADO", foreground=WARN)

    def _refresh_historico(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        q=self.var_hist_busca.get().lower() if hasattr(self,"var_hist_busca") else ""
        status_f=self.var_hist_status.get() if hasattr(self,"var_hist_status") else "TODOS"

        logs=self.repo.list_all_logs()
        if status_f!="TODOS": logs=[l for l in logs if l.status.value==status_f]
        if q: logs=[l for l in logs if
                    q in l.client_name.lower() or q in l.task_name.lower() or
                    q in l.document_filename.lower() or q in l.department.lower()]

        for log in logs:
            self.hist_tree.insert("","end",iid=log.id,
                values=(log.sent_at_formatted(), log.task_name, log.client_name,
                        log.department, log.document_filename, log.status.value, log.sent_by),
                tags=(log.status.value,))

        self.var_hist_total.set(f"{len(logs)} registro(s)")

    def _on_select_hist(self,event):
        sel=self.hist_tree.selection()
        if not sel:
            self.btn_download.config(state="disabled"); return
        log=self.repo._email_logs.get(sel[0])
        if not log:
            self.btn_download.config(state="disabled"); return

        dest_str=", ".join(log.recipients) if log.recipients else "—"
        erro_str=f"\nErro       : {log.error_message}" if log.error_message else ""
        detalhe=(
            f"ID         : {log.id}  |  "
            f"Status     : {log.status.value}  |  "
            f"Data/Hora  : {log.sent_at_formatted()}\n"
            f"Tarefa     : {log.task_name}  |  "
            f"Depto      : {log.department}  |  "
            f"Competência: {log.competence}\n"
            f"Empresa    : {log.client_name}\n"
            f"Documento  : {log.document_filename}\n"
            f"Destinatários: {dest_str}\n"
            f"Enviado por: {log.sent_by}"
            f"{erro_str}"
        )
        self.var_hist_detalhe.set(detalhe)

        # Habilita download só se o arquivo existir
        pode_baixar=bool(log.document_stored_path and os.path.exists(log.document_stored_path))
        self.btn_download.config(state="normal" if pode_baixar else "disabled")
        self._log_selecionado=log

    def _baixar_pdf_historico(self):
        if not hasattr(self,"_log_selecionado"): return
        log=self._log_selecionado
        if not log.document_stored_path or not os.path.exists(log.document_stored_path):
            messagebox.showerror("Arquivo não encontrado","O PDF não está mais disponível no servidor."); return
        dest=filedialog.asksaveasfilename(
            title="Salvar PDF",
            initialfile=log.document_filename,
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")])
        if dest:
            shutil.copy2(log.document_stored_path,dest)
            messagebox.showinfo("Salvo",f"PDF salvo em:\n{dest}")

    # ── LOG ───────────────────────────────────────────────────────────

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

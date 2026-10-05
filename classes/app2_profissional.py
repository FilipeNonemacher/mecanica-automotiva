import os
import sqlite3
import hashlib
import re
import tempfile
from datetime import date
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from PIL import Image, ImageChops, ImageOps

from funcoes import Funcoes, valor_em_centavos, formatar_reais, gerar_pdf_orcamento



# CONFIGURAÇÃO GERAL

DB_PATH = "bd_oficina"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTAS_IMAGENS = [
    os.path.join(BASE_DIR, "imagens", "fundo"),
    os.path.join(os.path.dirname(BASE_DIR), "imagens", "fundo"),
]
DIR_IMAGENS = next((p for p in PASTAS_IMAGENS if os.path.isdir(p)), PASTAS_IMAGENS[0])

# Menu em cinza claro com um toque de verde; área de trabalho em grafite.
COR_FUNDO = "#202628"
COR_LATERAL = "#EDF1ED"
COR_SUPERFICIE = "#282F32"
COR_SUPERFICIE_2 = "#22282B"
COR_BORDA = "#424B4E"
COR_TEXTO = "#F1F4F2"
COR_TEXTO_2 = "#C0C9C5"
COR_TEXTO_3 = "#9EABA5"
COR_AZUL = "#477C69"
COR_AZUL_HOVER = "#3A6857"
COR_BOTAO = "#384346"
COR_BOTAO_HOVER = "#455255"
COR_MENU_TEXTO = "#283B32"
COR_MENU_SECUNDARIO = "#596D61"
COR_MENU_ATIVO = "#D3E1D7"
COR_MENU_HOVER = "#E0E8E0"
COR_MENU_BORDA = "#D1DBD2"
COR_LOGO = "#263C31"
COR_VERDE = "#238636"
COR_VERDE_HOVER = "#2EA043"
COR_VERMELHO = "#B42318"
COR_VERMELHO_HOVER = "#912018"
COR_AMARELO = "#A16207"
COR_AMARELO_HOVER = "#854D0E"

FONTE = "Segoe UI"
FONTE_TITULO = (FONTE, 24, "bold")
FONTE_SECAO = (FONTE, 15, "bold")
FONTE_CORPO = (FONTE, 13)
FONTE_LABEL = (FONTE, 12, "bold")
FONTE_AUXILIAR = (FONTE, 12)
FONTE_BOTAO = (FONTE, 13, "bold")
LARGURA_MENU = 280
MARGEM_PAGINA = 24


def configurar_tipografia(janela):
    """Usa uma fonte de interface instalada, com a mesma escala em todas as telas."""
    global FONTE, FONTE_TITULO, FONTE_SECAO, FONTE_CORPO
    global FONTE_LABEL, FONTE_AUXILIAR, FONTE_BOTAO
    disponiveis = set(tkfont.families(janela))
    FONTE = next((nome for nome in ("Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial")
                  if nome in disponiveis), tkfont.nametofont("TkDefaultFont", root=janela).actual("family"))
    FONTE_TITULO = (FONTE, 24, "bold")
    FONTE_SECAO = (FONTE, 15, "bold")
    FONTE_CORPO = (FONTE, 13)
    FONTE_LABEL = (FONTE, 12, "bold")
    FONTE_AUXILIAR = (FONTE, 12)
    FONTE_BOTAO = (FONTE, 13, "bold")


def carregar_logo(nome, limite):
    """Exibe a marca em tom escuro sem deformar nem alterar o PNG original."""
    caminho = os.path.join(DIR_IMAGENS, nome)
    if not os.path.isfile(caminho):
        return None
    try:
        with Image.open(caminho) as original:
            imagem = original.convert("RGBA")
        alpha = imagem.getchannel("A")
        if alpha.getextrema() == (255, 255):
            # Compatibilidade com uma marca monocromática em fundo sólido.
            rgb = imagem.convert("RGB")
            fundo = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
            alpha = ImageOps.grayscale(ImageChops.difference(rgb, fundo))
        limites = alpha.point(lambda valor: 255 if valor > 8 else 0).getbbox()
        if limites is None:
            return None
        alpha = alpha.crop(limites)
        marca = Image.new("RGBA", alpha.size, COR_LOGO)
        marca.putalpha(alpha)
        escala = min(limite[0] / marca.width, limite[1] / marca.height)
        tamanho = (max(1, round(marca.width * escala)), max(1, round(marca.height * escala)))
        return ctk.CTkImage(light_image=marca, dark_image=marca, size=tamanho)
    except (OSError, ValueError):
        return None


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def preparar_usuarios():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        existe = conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO usuarios (usuario, senha_hash, nome) VALUES (?, ?, ?)",
                ("admin", hash_senha("admin123"), "Administrador"),
            )



# LOGIN

class Login:
    def __init__(self, janela):
        self.janela = janela
        configurar_tipografia(janela)
        self.janela.title("Acesso | Gestão de Oficina")
        self.janela.geometry("1040x640")
        self.janela.minsize(920, 580)
        self.janela.configure(fg_color=COR_FUNDO)
        self.janela.protocol("WM_DELETE_WINDOW", self.janela.destroy)
        self._montar()

    def _montar(self):
        self.container = ctk.CTkFrame(self.janela, fg_color=COR_FUNDO, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, minsize=360, weight=0)
        self.container.grid_columnconfigure(1, weight=1)

        # Painel institucional fixo. O logo não ultrapassa mais a largura disponível.
        painel_marca = ctk.CTkFrame(
            self.container,
            width=360,
            fg_color=COR_LATERAL,
            corner_radius=0,
            border_width=0,
        )
        painel_marca.grid(row=0, column=0, sticky="nsew")
        painel_marca.grid_propagate(False)
        painel_marca.grid_columnconfigure(0, weight=1)
        painel_marca.grid_rowconfigure(0, weight=1)
        painel_marca.grid_rowconfigure(4, weight=1)

        self.login_logo = carregar_logo("escrito.png", (260, 64))
        self.login_simbolo = carregar_logo("logo1.png", (100, 84))
        marca = ctk.CTkFrame(painel_marca, fg_color="transparent")
        marca.grid(row=1, column=0, padx=32, pady=(0, 28), sticky="ew")
        marca.grid_columnconfigure(0, weight=1)
        if self.login_simbolo:
            ctk.CTkLabel(marca, image=self.login_simbolo, text="").grid(row=0, column=0, pady=(0, 18))
        if self.login_logo:
            ctk.CTkLabel(marca, image=self.login_logo, text="").grid(row=1, column=0)
        else:
            ctk.CTkLabel(marca, text="MECÂNICA", font=FONTE_TITULO,
                         text_color=COR_LOGO).grid(row=1, column=0)
            ctk.CTkLabel(marca, text="AUTOMOTIVA", font=FONTE_LABEL,
                         text_color=COR_MENU_SECUNDARIO).grid(row=2, column=0, pady=(2, 0))
        ctk.CTkLabel(painel_marca, text="Gestão de oficina", font=FONTE_SECAO,
                     text_color=COR_MENU_TEXTO).grid(row=2, column=0, padx=34, sticky="w")
        ctk.CTkLabel(painel_marca,
                     text="Clientes, veículos e ordens de serviço\nem um único ambiente.",
                     font=FONTE_CORPO, text_color=COR_MENU_SECUNDARIO,
                     justify="left").grid(row=3, column=0, padx=34, pady=(0, 0), sticky="w")

        area_login = ctk.CTkFrame(self.container, fg_color=COR_FUNDO, corner_radius=0)
        area_login.grid(row=0, column=1, sticky="nsew")
        area_login.grid_columnconfigure(0, weight=1)
        area_login.grid_rowconfigure(0, weight=1)
        area_login.grid_rowconfigure(2, weight=1)

        # O formulário tem largura controlada e fica centralizado. Isso evita campos esticados/cortados.
        formulario = ctk.CTkFrame(area_login, width=390, fg_color="transparent", corner_radius=0)
        formulario.grid(row=1, column=0, padx=46, pady=30)
        # A altura é calculada pelos campos. Fixá-la na altura padrão do
        # CTkFrame (200 px) escondia a senha, a mensagem e o botão Entrar.
        formulario.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            formulario,
            text="Acessar sistema",
            font=FONTE_TITULO,
            text_color=COR_TEXTO,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            formulario,
            text="Informe suas credenciais para continuar.",
            font=FONTE_CORPO,
            text_color=COR_TEXTO_2,
        ).grid(row=1, column=0, sticky="w", pady=(0, 28))

        self._label_login(formulario, "Usuário", 2)
        self.entry_usuario = ctk.CTkEntry(
            formulario,
            width=390,
            height=44,
            corner_radius=5,
            fg_color=COR_SUPERFICIE_2,
            border_color=COR_BORDA,
            border_width=1,
            text_color=COR_TEXTO,
            placeholder_text="Digite seu usuário",
            font=FONTE_CORPO,
        )
        self.entry_usuario.grid(row=3, column=0, sticky="ew", pady=(0, 18))

        self._label_login(formulario, "Senha", 4)
        self.entry_senha = ctk.CTkEntry(
            formulario,
            height=44,
            corner_radius=5,
            fg_color=COR_SUPERFICIE_2,
            border_color=COR_BORDA,
            border_width=1,
            text_color=COR_TEXTO,
            placeholder_text="Digite sua senha",
            show="•",
            font=FONTE_CORPO,
        )
        self.entry_senha.grid(row=5, column=0, sticky="ew")

        self.lbl_erro = ctk.CTkLabel(
            formulario,
            text="",
            height=24,
            font=FONTE_CORPO,
            text_color="#F87171",
        )
        self.lbl_erro.grid(row=6, column=0, sticky="w", pady=(8, 4))

        ctk.CTkButton(
            formulario,
            text="Entrar",
            height=44,
            corner_radius=5,
            fg_color=COR_AZUL,
            hover_color=COR_AZUL_HOVER,
            font=FONTE_BOTAO,
            command=self.autenticar,
        ).grid(row=7, column=0, sticky="ew", pady=(4, 0))

        self.entry_usuario.bind("<Return>", lambda _e: self.entry_senha.focus())
        self.entry_senha.bind("<Return>", lambda _e: self.autenticar())
        self.entry_usuario.focus()

    def _label_login(self, parent, texto, row):
        ctk.CTkLabel(
            parent,
            text=texto,
            font=FONTE_LABEL,
            text_color=COR_TEXTO_2,
        ).grid(row=row, column=0, sticky="w", pady=(0, 6))

    def autenticar(self):
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get()

        if not usuario or not senha:
            self.lbl_erro.configure(text="Preencha usuário e senha.")
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                dados = conn.execute(
                    "SELECT nome FROM usuarios WHERE usuario=? AND senha_hash=? AND ativo=1",
                    (usuario, hash_senha(senha)),
                ).fetchone()
        except sqlite3.Error:
            self.lbl_erro.configure(text="Não foi possível acessar o banco de dados.")
            return

        if not dados:
            self.lbl_erro.configure(text="Usuário ou senha inválidos.")
            self.entry_senha.delete(0, "end")
            self.entry_senha.focus()
            return

        self.container.destroy()
        Aplicacao(self.janela, dados[0])



# APLICAÇÃO PRINCIPAL

class Aplicacao(Funcoes):
    def __init__(self, janela, nome_usuario="Administrador"):
        self.janela = janela
        configurar_tipografia(janela)
        self.nome_usuario = nome_usuario
        self.guardar_imagens = []
        self.id_veiculo = None
        self._pagina_atual = None
        # O rascunho permanece na memória ao navegar entre as abas desta sessão.
        self.orc_itens = []
        self._orc_edicao = None
        self._orc_cliente_var = ctk.StringVar(master=janela)
        self._orc_placa_var = ctk.StringVar(master=janela)
        self._orc_servico_var = ctk.StringVar(master=janela)
        self._orc_valor_var = ctk.StringVar(master=janela)
        self._orc_observacoes_var = ctk.StringVar(master=janela)

        self.tela()
        self.criar_bd()
        self._montar_shell()
        self.mostrar_inicio()

    def tela(self):
        self.janela.title("Gestão de Oficina")
        self.janela.geometry("1280x720")
        self.janela.minsize(1000, 640)
        self.janela.configure(fg_color=COR_FUNDO)

    # ESTRUTURA BASE
    def _montar_shell(self):
        for widget in self.janela.winfo_children():
            widget.destroy()

        self.janela.grid_rowconfigure(0, weight=1)
        self.janela.grid_columnconfigure(0, minsize=LARGURA_MENU, weight=0)
        self.janela.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.janela,
            width=LARGURA_MENU,
            fg_color=COR_LATERAL,
            corner_radius=0,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(8, weight=1)

        self._montar_marca_sidebar()

        ctk.CTkLabel(
            self.sidebar,
            text="Menu",
            font=FONTE_LABEL,
            text_color=COR_MENU_SECUNDARIO,
        ).grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")

        self.botoes_menu = {}
        itens = [
            ("inicio", "Início", self.mostrar_inicio),
            ("cadastro", "Cadastrar cliente e veículo", self.mostrar_cadastro),
            ("clientes", "Visualizar clientes", self.mostrar_clientes),
            ("os", "Ordem de serviço", self.mostrar_os),
            ("orcamento", "Orçamento", self.mostrar_orcamento),
        ]

        for linha, (chave, texto, comando) in enumerate(itens, start=2):
            botao = ctk.CTkButton(
                self.sidebar,
                text=texto,
                command=comando,
                anchor="w",
                height=44,
                corner_radius=5,
                fg_color="transparent",
                hover_color=COR_MENU_HOVER,
                text_color=COR_MENU_TEXTO,
                font=FONTE_CORPO,
            )
            botao.grid(row=linha, column=0, padx=16, pady=3, sticky="ew")
            self.botoes_menu[chave] = botao

        sessao = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        sessao.grid(row=9, column=0, padx=24, pady=24, sticky="sew")

        ctk.CTkFrame(sessao, height=1, fg_color=COR_MENU_BORDA).pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            sessao,
            text=self.nome_usuario,
            font=FONTE_LABEL,
            text_color=COR_MENU_TEXTO,
        ).pack(anchor="w")
        ctk.CTkLabel(
            sessao,
            text="Sessão ativa",
            font=FONTE_AUXILIAR,
            text_color=COR_MENU_SECUNDARIO,
        ).pack(anchor="w", pady=(2, 10))
        ctk.CTkButton(
            sessao,
            text="Encerrar sessão",
            height=36,
            corner_radius=5,
            fg_color=COR_MENU_ATIVO,
            hover_color=COR_MENU_HOVER,
            text_color=COR_MENU_TEXTO,
            font=FONTE_LABEL,
            command=self.logout,
        ).pack(fill="x")

        self.area = ctk.CTkFrame(self.janela, fg_color=COR_FUNDO, corner_radius=0)
        self.area.grid(row=0, column=1, sticky="nsew")
        self.area.grid_rowconfigure(1, weight=1)
        self.area.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self.area, fg_color=COR_FUNDO, corner_radius=0, height=82)
        self.header.grid(row=0, column=0, sticky="ew", padx=MARGEM_PAGINA, pady=(24, 16))
        # Cabeçalho acompanha a altura real do título e subtítulo.
        self.header.grid_columnconfigure(0, weight=1)

        self.titulo_pagina = ctk.CTkLabel(
            self.header,
            text="",
            font=FONTE_TITULO,
            text_color=COR_TEXTO,
            anchor="w",
        )
        self.titulo_pagina.grid(row=0, column=0, sticky="ew", pady=(6, 0))

        self.subtitulo_pagina = ctk.CTkLabel(
            self.header,
            text="",
            font=FONTE_CORPO,
            text_color=COR_TEXTO_2,
            anchor="w",
        )
        self.subtitulo_pagina.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self.host = ctk.CTkFrame(self.area, fg_color="transparent", corner_radius=0)
        self.host.grid(row=1, column=0, sticky="nsew", padx=MARGEM_PAGINA, pady=(0, 24))
        self.host.grid_rowconfigure(0, weight=1)
        self.host.grid_columnconfigure(0, weight=1)

    def _montar_marca_sidebar(self):
        bloco = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        bloco.grid(row=0, column=0, sticky="ew", padx=24, pady=(28, 16))
        bloco.grid_columnconfigure(0, weight=1)
        self.sidebar_simbolo = carregar_logo("logo1.png", (76, 68))
        self.sidebar_logo = carregar_logo("escrito.png", (224, 48))
        if self.sidebar_simbolo:
            self.guardar_imagens.append(self.sidebar_simbolo)
            ctk.CTkLabel(bloco, image=self.sidebar_simbolo, text="").grid(row=0, column=0, pady=(0, 12))
        if self.sidebar_logo:
            self.guardar_imagens.append(self.sidebar_logo)
            ctk.CTkLabel(bloco, image=self.sidebar_logo, text="").grid(row=1, column=0)
        else:
            ctk.CTkLabel(bloco, text="MECÂNICA", font=(FONTE, 22, "bold"),
                         text_color=COR_LOGO).grid(row=1, column=0)
            ctk.CTkLabel(bloco, text="AUTOMOTIVA", font=FONTE_LABEL,
                         text_color=COR_MENU_SECUNDARIO).grid(row=2, column=0, pady=(2, 0))
        ctk.CTkFrame(bloco, height=1, fg_color=COR_MENU_BORDA).grid(
            row=3, column=0, sticky="ew", pady=(24, 0))

    def _abrir_pagina(self, chave, titulo, subtitulo):
        self._pagina_atual = chave

        for widget in self.host.winfo_children():
            widget.destroy()

        self.titulo_pagina.configure(text=titulo)
        self.subtitulo_pagina.configure(text=subtitulo)

        for nome, botao in self.botoes_menu.items():
            ativo = nome == chave
            botao.configure(
                fg_color=COR_MENU_ATIVO if ativo else "transparent",
                text_color=COR_MENU_TEXTO,
                font=FONTE_BOTAO if ativo else FONTE_CORPO,
            )

    # HELPERS VISUAIS 
    def _scroll_page(self):
        page = ctk.CTkScrollableFrame(
            self.host,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COR_BORDA,
            scrollbar_button_hover_color=COR_BOTAO_HOVER,
        )
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        return page

    def _surface(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=COR_SUPERFICIE,
            corner_radius=7,
            border_width=1,
            border_color=COR_BORDA,
        )

    def _action_bar(self):
        # As ações ficam visíveis mesmo quando o formulário precisa de rolagem.
        barra = ctk.CTkFrame(self.host, fg_color="transparent", corner_radius=0)
        barra.grid(row=1, column=0, sticky="e", padx=22, pady=(16, 0))
        return barra

    def _section_title(self, parent, texto, row, columnspan=2, pady=(20, 16), compact=False):
        container = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        container.grid(row=row, column=0, columnspan=columnspan, sticky="ew", padx=22, pady=pady)
        container.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            container,
            text=texto,
            font=FONTE_SECAO,
            text_color=COR_TEXTO,
            height=20 if compact else 28,
        ).grid(row=0, column=0, sticky="w")
        if not compact:
            ctk.CTkFrame(container, height=1, fg_color=COR_BORDA).grid(
                row=1, column=0, sticky="ew", pady=(10, 0)
            )

    def _label(self, parent, texto, row, column, columnspan=1, padx=(0, 0)):
        lbl = ctk.CTkLabel(
            parent,
            text=texto,
            font=FONTE_LABEL,
            text_color=COR_TEXTO_2,
            anchor="w",
        )
        lbl.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=(22 + padx[0], 22 + padx[1]),
            pady=(4, 5),
        )
        return lbl

    def _entry(self, parent, placeholder, row, column, columnspan=1, padx=(0, 0), textvariable=None):
        ent = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            height=40,
            corner_radius=5,
            fg_color=COR_SUPERFICIE_2,
            border_color=COR_BORDA,
            border_width=1,
            text_color=COR_TEXTO,
            font=FONTE_CORPO,
            textvariable=textvariable,
        )
        ent.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=(22 + padx[0], 22 + padx[1]),
            pady=(0, 12),
        )
        return ent

    def _primary_button(self, parent, text, command, width=150):
        return ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=40,
            corner_radius=5,
            fg_color=COR_AZUL,
            hover_color=COR_AZUL_HOVER,
            font=FONTE_BOTAO,
            text_color=COR_TEXTO,
            command=command,
        )

    def _secondary_button(self, parent, text, command, width=110):
        return ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=40,
            corner_radius=5,
            fg_color=COR_BOTAO,
            hover_color=COR_BOTAO_HOVER,
            font=FONTE_BOTAO,
            text_color=COR_TEXTO,
            command=command,
        )

    # INÍCIO
    def mostrar_inicio(self):
        self._abrir_pagina(
            "inicio",
            "Visão geral",
            "Resumo da operação e acesso às rotinas mais utilizadas.",
        )

        page = self._scroll_page()

        resumo = self._surface(page)
        resumo.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        resumo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            resumo,
            text="Resumo",
            font=FONTE_SECAO,
            text_color=COR_TEXTO,
        ).grid(row=0, column=0, padx=22, pady=(18, 12), sticky="w")

        dados = self._obter_resumo()
        for i, (rotulo, valor) in enumerate(dados):
            linha = ctk.CTkFrame(resumo, fg_color="transparent", corner_radius=0)
            linha.grid(row=i + 1, column=0, sticky="ew", padx=22)
            linha.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                linha,
                text=rotulo,
                font=FONTE_CORPO,
                text_color=COR_TEXTO_2,
            ).grid(row=0, column=0, sticky="w", pady=10)
            ctk.CTkLabel(
                linha,
                text=str(valor),
                font=FONTE_BOTAO,
                text_color=COR_TEXTO,
            ).grid(row=0, column=1, sticky="e", pady=10)
            if i < len(dados) - 1:
                ctk.CTkFrame(linha, height=1, fg_color=COR_BORDA).grid(
                    row=1, column=0, columnspan=2, sticky="ew"
                )

        ctk.CTkFrame(resumo, height=8, fg_color="transparent").grid(
            row=len(dados) + 1, column=0
        )

        acoes = self._surface(page)
        acoes.grid(row=1, column=0, sticky="ew")
        acoes.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            acoes,
            text="Acesso rápido",
            font=FONTE_SECAO,
            text_color=COR_TEXTO,
        ).grid(row=0, column=0, padx=22, pady=(18, 8), sticky="w")

        itens = [
            ("Novo cliente e veículo", "Cadastrar cliente e vincular um veículo", self.mostrar_cadastro),
            ("Consultar clientes", "Pesquisar cadastros e veículos", self.mostrar_clientes),
            ("Nova ordem de serviço", "Abrir ou localizar uma O.S.", self.mostrar_os),
            ("Orçamento", "Preparar uma estimativa de serviços", self.mostrar_orcamento),
        ]

        for i, (titulo, descricao, comando) in enumerate(itens, start=1):
            linha = ctk.CTkFrame(acoes, fg_color="transparent", corner_radius=0)
            linha.grid(row=i, column=0, sticky="ew", padx=22)
            linha.grid_columnconfigure(0, weight=1)

            bloco_texto = ctk.CTkFrame(linha, fg_color="transparent", corner_radius=0)
            bloco_texto.grid(row=0, column=0, sticky="w", pady=11)
            ctk.CTkLabel(
                bloco_texto,
                text=titulo,
                font=FONTE_LABEL,
                text_color=COR_TEXTO,
            ).pack(anchor="w")
            ctk.CTkLabel(
                bloco_texto,
                text=descricao,
                font=FONTE_AUXILIAR,
                text_color=COR_TEXTO_3,
            ).pack(anchor="w", pady=(2, 0))

            self._secondary_button(linha, "Abrir", comando, width=86).grid(
                row=0, column=1, sticky="e"
            )

            if i < len(itens):
                ctk.CTkFrame(linha, height=1, fg_color=COR_BORDA).grid(
                    row=1, column=0, columnspan=2, sticky="ew"
                )

        ctk.CTkFrame(acoes, height=8, fg_color="transparent").grid(
            row=len(itens) + 1, column=0
        )

    def _obter_resumo(self):
        try:
            self.connect_bd()
            clientes = self.cursor.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
            veiculos = self.cursor.execute("SELECT COUNT(*) FROM veiculos").fetchone()[0]
            ordens = self.cursor.execute("SELECT COUNT(*) FROM ordens_servico").fetchone()[0]
            abertas = self.cursor.execute(
                "SELECT COUNT(*) FROM ordens_servico WHERE status='Aberto'"
            ).fetchone()[0]
            return [
                ("Clientes cadastrados", clientes),
                ("Veículos cadastrados", veiculos),
                ("Ordens de serviço", ordens),
                ("Ordens em aberto", abertas),
            ]
        except sqlite3.Error:
            return [
                ("Clientes cadastrados", "—"),
                ("Veículos cadastrados", "—"),
                ("Ordens de serviço", "—"),
                ("Ordens em aberto", "—"),
            ]
        finally:
            try:
                self.disconnect_bd()
            except Exception:
                pass

    # CADASTRO
    def mostrar_cadastro(self):
        self._abrir_pagina(
            "cadastro",
            "Cadastrar cliente e veículo",
            "Preencha os dados abaixo para criar um novo cadastro.",
        )

        page = self._scroll_page()
        form = self._surface(page)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        form.grid_columnconfigure((0, 1), weight=1, uniform="formulario")

        self._section_title(form, "Dados do cliente", 0)

        self._label(form, "Código", 1, 0)
        self._label(form, "Nome completo", 1, 1)
        self.entry_id_cliente = self._entry(form, "Automático", 2, 0)
        self.entry_id_cliente.configure(state="normal")
        self.entry_nome = self._entry(form, "Nome do cliente", 2, 1)

        self._label(form, "CPF", 3, 0)
        self._label(form, "Telefone", 3, 1)
        self.entry_cpf = self._entry(form, "000.000.000-00", 4, 0)
        self.entry_telefone = self._entry(form, "(00) 00000-0000", 4, 1)

        self._label(form, "Endereço", 5, 0, columnspan=2)
        self.entry_endereco = self._entry(form, "Rua, número, bairro", 6, 0, columnspan=2)

        self._section_title(form, "Veículo vinculado", 7, pady=(14, 14))

        self._label(form, "Placa", 8, 0)
        self._label(form, "Ano", 8, 1)
        self.entry_placa = self._entry(form, "ABC1D23", 9, 0)
        self.entry_ano = self._entry(form, "2026", 9, 1)

        self._label(form, "Marca", 10, 0)
        self._label(form, "Modelo", 10, 1)
        self.entry_marca = self._entry(form, "Marca", 11, 0)
        self.entry_modelo = self._entry(form, "Modelo", 11, 1)

        self.area_acoes_cadastro = self._action_bar()

        self._secondary_button(
            self.area_acoes_cadastro, "Limpar", self.limpar_tela, width=105
        ).pack(side="left", padx=(0, 8))
        self._primary_button(
            self.area_acoes_cadastro, "Salvar cadastro", self.cadastrar_cliente, width=145
        ).pack(side="left")

    # CLIENTES
    def mostrar_clientes(self):
        self._abrir_pagina(
            "clientes",
            "Visualizar clientes",
            "Pesquise e selecione um cadastro para consultar ou editar.",
        )

        painel = self._surface(self.host)
        painel.grid(row=0, column=0, sticky="nsew", pady=(0, 0))
        painel.grid_rowconfigure(1, weight=1)
        painel.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(painel, fg_color="transparent", corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew", padx=22, pady=16)
        toolbar.grid_columnconfigure(0, weight=1)

        self.entry_busca_cliente = ctk.CTkEntry(
            toolbar,
            placeholder_text="Pesquisar por nome, telefone ou placa",
            height=40,
            corner_radius=5,
            fg_color=COR_SUPERFICIE_2,
            border_color=COR_BORDA,
            border_width=1,
            font=FONTE_CORPO,
            text_color=COR_TEXTO,
        )
        self.entry_busca_cliente.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._secondary_button(toolbar, "Atualizar", self.exibir_clientes, width=96).grid(
            row=0, column=1
        )

        self._criar_treeview(painel)

        rodape = ctk.CTkFrame(painel, fg_color="transparent", corner_radius=0)
        rodape.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        rodape.grid_columnconfigure(0, weight=1)

        self.lbl_quantidade = ctk.CTkLabel(
            rodape,
            text="0 registros",
            font=FONTE_AUXILIAR,
            text_color=COR_TEXTO_3,
        )
        self.lbl_quantidade.grid(row=0, column=0, sticky="w")

        self._secondary_button(
            rodape, "Abrir cadastro", self._abrir_edicao_cliente, width=118
        ).grid(row=0, column=1, padx=(8, 0))

        self.entry_busca_cliente.bind("<KeyRelease>", lambda _e: self.filtrar_treeview())
        self.exibir_clientes()

    def _criar_treeview(self, parent):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            style.theme_use("default")

        style.configure(
            "Oficina.Treeview",
            background=COR_SUPERFICIE_2,
            foreground=COR_TEXTO,
            fieldbackground=COR_SUPERFICIE_2,
            borderwidth=0,
            rowheight=38,
            font=(FONTE, -13),
        )
        style.configure(
            "Oficina.Treeview.Heading",
            background=COR_BOTAO,
            foreground=COR_TEXTO,
            relief="flat",
            borderwidth=0,
            font=(FONTE, -12, "bold"),
            padding=(10, 10),
        )
        style.map(
            "Oficina.Treeview",
            background=[("selected", COR_AZUL)],
            foreground=[("selected", "#FFFFFF")],
        )

        tabela_area = ctk.CTkFrame(parent, fg_color=COR_SUPERFICIE_2, corner_radius=0)
        tabela_area.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 12))
        tabela_area.grid_rowconfigure(0, weight=1)
        tabela_area.grid_columnconfigure(0, weight=1)

        colunas = ("cod", "nome", "telefone", "veiculo", "placa", "os", "valor")
        self.tv = ttk.Treeview(
            tabela_area,
            columns=colunas,
            show="headings",
            style="Oficina.Treeview",
            selectmode="browse",
        )

        cabecalhos = {
            "cod": "Cód.",
            "nome": "Cliente",
            "telefone": "Telefone",
            "veiculo": "Veículo / Modelo",
            "placa": "Placa",
            "os": "Nº O.S.",
            "valor": "Valor (R$)",
        }
        for coluna in colunas:
            self.tv.heading(coluna, text=cabecalhos[coluna])

        # minwidth + stretch evita cortes. Quando não couber, aparece barra horizontal.
        self.tv.column("cod", width=55, minwidth=55, stretch=False, anchor="center")
        self.tv.column("nome", width=200, minwidth=160, stretch=True)
        self.tv.column("telefone", width=130, minwidth=120, stretch=False)
        self.tv.column("veiculo", width=180, minwidth=160, stretch=True)
        self.tv.column("placa", width=100, minwidth=90, stretch=False, anchor="center")
        self.tv.column("os", width=75, minwidth=75, stretch=False, anchor="center")
        self.tv.column("valor", width=100, minwidth=95, stretch=False, anchor="e")
        for coluna in colunas:
            self.tv.heading(coluna, anchor=self.tv.column(coluna, "anchor"))

        self.tv.grid(row=0, column=0, sticky="nsew")

        scroll_y = ctk.CTkScrollbar(tabela_area, orientation="vertical", command=self.tv.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")

        scroll_x = ctk.CTkScrollbar(tabela_area, orientation="horizontal", command=self.tv.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tv.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tv.bind("<Double-1>", self._abrir_edicao_cliente)

    def filtrar_treeview(self):
        termo = self.entry_busca_cliente.get().strip().lower()
        self.exibir_clientes()

        if termo:
            for item in self.tv.get_children():
                valores = " ".join(str(v).lower() for v in self.tv.item(item, "values"))
                if termo not in valores:
                    self.tv.detach(item)

        self._atualizar_quantidade_clientes()

    def _atualizar_quantidade_clientes(self):
        if hasattr(self, "lbl_quantidade") and self.lbl_quantidade.winfo_exists():
            total = len(self.tv.get_children()) if hasattr(self, "tv") else 0
            texto = "1 registro" if total == 1 else f"{total} registros"
            self.lbl_quantidade.configure(text=texto)

    def _abrir_edicao_cliente(self, event=None):
        if not hasattr(self, "tv") or not self.tv.winfo_exists():
            return

        selecionado = self.tv.selection()
        if not selecionado:
            messagebox.showinfo("Clientes", "Selecione um cadastro para abrir.")
            return

        item = selecionado[0]
        id_cliente = self.tv.item(item, "values")[0]
        id_veiculo = self.veiculos_linhas.get(item)

        self.connect_bd()
        cliente = self.cursor.execute(
            "SELECT nome, cpf, telefone, endereco FROM clientes WHERE id_cliente=?",
            (id_cliente,),
        ).fetchone()
        veiculo = (
            self.cursor.execute(
                "SELECT placa, marca, modelo, ano FROM veiculos WHERE id_veiculo=?",
                (id_veiculo,),
            ).fetchone()
            if id_veiculo
            else None
        )
        self.disconnect_bd()

        if not cliente:
            messagebox.showwarning("Clientes", "Cadastro não encontrado.")
            return

        self.mostrar_cadastro()
        self.id_veiculo = id_veiculo

        valores_cliente = (id_cliente, *cliente)
        campos_cliente = (
            self.entry_id_cliente,
            self.entry_nome,
            self.entry_cpf,
            self.entry_telefone,
            self.entry_endereco,
        )
        for campo, valor in zip(campos_cliente, valores_cliente):
            campo.delete(0, "end")
            campo.insert(0, "" if valor is None else str(valor))

        if veiculo:
            campos_veiculo = (
                self.entry_placa,
                self.entry_marca,
                self.entry_modelo,
                self.entry_ano,
            )
            for campo, valor in zip(campos_veiculo, veiculo):
                campo.delete(0, "end")
                campo.insert(0, "" if valor is None else str(valor))

        for widget in self.area_acoes_cadastro.winfo_children():
            widget.destroy()

        self._secondary_button(
            self.area_acoes_cadastro, "Cancelar", self.mostrar_clientes, width=100
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            self.area_acoes_cadastro,
            text="Excluir",
            width=100,
            height=40,
            corner_radius=5,
            fg_color=COR_VERMELHO,
            hover_color=COR_VERMELHO_HOVER,
            font=FONTE_BOTAO,
            command=self.excluir_cliente,
        ).pack(side="left", padx=(0, 8))

        self._primary_button(
            self.area_acoes_cadastro, "Salvar alterações", self.editar_cliente, width=140
        ).pack(side="left")

    # ORDEM DE SERVIÇO
    def mostrar_os(self):
        self._abrir_pagina(
            "os",
            "Ordem de serviço",
            "Abra uma nova ordem ou localize uma ordem existente.",
        )

        page = self._scroll_page()
        form = self._surface(page)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        form.grid_columnconfigure((0, 1), weight=1, uniform="formulario")

        self._section_title(form, "Identificação", 0)

        self._label(form, "Nº O.S.", 1, 0)
        self._label(form, "Placa do veículo", 1, 1)
        self.entry_num_os = self._entry(form, "Número para pesquisa", 2, 0)
        self.entry_os_placa = self._entry(form, "Informe a placa", 2, 1)

        self._section_title(form, "Serviço", 3, pady=(10, 14))

        self._label(form, "Descrição do problema / serviço", 4, 0, columnspan=2)
        self.entry_descricao = ctk.CTkTextbox(
            form,
            height=180,
            corner_radius=5,
            fg_color=COR_SUPERFICIE_2,
            border_width=1,
            border_color=COR_BORDA,
            text_color=COR_TEXTO,
            font=FONTE_CORPO,
        )
        self.entry_descricao.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 12)
        )

        self._label(form, "Valor total (R$)", 6, 0)
        self.entry_valor = self._entry(form, "0,00", 7, 0)

        acoes = self._action_bar()

        self._secondary_button(acoes, "Pesquisar", self.pesquisar_os, width=100).pack(
            side="left", padx=(0, 8)
        )

        ctk.CTkButton(
            acoes,
            text="Editar O.S.",
            width=105,
            height=40,
            corner_radius=5,
            fg_color=COR_AMARELO,
            hover_color=COR_AMARELO_HOVER,
            font=FONTE_BOTAO,
            command=self.editar_ordem,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            acoes,
            text="Excluir O.S.",
            width=105,
            height=40,
            corner_radius=5,
            fg_color=COR_VERMELHO,
            hover_color=COR_VERMELHO_HOVER,
            font=FONTE_BOTAO,
            command=self.excluir_ordem,
        ).pack(side="left", padx=(0, 8))

        self._primary_button(acoes, "Gerar O.S.", self.cadastrar_ordem, width=110).pack(
            side="left"
        )

    # ORÇAMENTO 
    def mostrar_orcamento(self):
        self._abrir_pagina(
            "orcamento",
            "Orçamento",
            "Adicione serviços e peças, confira os valores e gere o orçamento em PDF.",
        )

        page = self._scroll_page()
        form = self._surface(page)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        form.grid_columnconfigure((0, 1), weight=1, uniform="formulario")

        self._section_title(form, "Dados do orçamento", 0, pady=(12, 8), compact=True)

        self._label(form, "Cliente", 1, 0).configure(height=20)
        self._label(form, "Placa do veículo", 1, 1).configure(height=20)
        self.orc_cliente = self._entry(form, "Nome do cliente", 2, 0, textvariable=self._orc_cliente_var)
        self.orc_placa = self._entry(form, "ABC1D23", 2, 1, textvariable=self._orc_placa_var)

        entrada = self._surface(page)
        entrada.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        entrada.grid_columnconfigure(0, weight=3)
        entrada.grid_columnconfigure(1, weight=1, minsize=155)
        self._section_title(entrada, "Adicionar serviço ou peça", 0, columnspan=3, pady=(12, 8), compact=True)
        self._label(entrada, "Descrição", 1, 0).configure(height=20)
        self._label(entrada, "Valor do item (R$)", 1, 1).configure(height=20)
        self.orc_servico = self._entry(entrada, "Ex.: troca de pneus", 2, 0, textvariable=self._orc_servico_var)
        self.orc_valor = self._entry(entrada, "Ex.: 150,00", 2, 1, textvariable=self._orc_valor_var)
        self.orc_servico.bind("<Return>", lambda event: self.orc_valor.focus_set())
        self.orc_valor.bind("<Return>", lambda event: self._adicionar_item_orcamento())
        self.btn_orc_adicionar = self._primary_button(
            entrada, "Adicionar item", self._adicionar_item_orcamento, width=150,
        )
        self.btn_orc_adicionar.grid(row=2, column=2, sticky="e", padx=(0, 22), pady=(0, 12))

        lista = self._surface(page)
        lista.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        lista.grid_columnconfigure(0, weight=1)

        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Orcamento.Treeview", background=COR_SUPERFICIE_2,
                          foreground=COR_TEXTO, fieldbackground=COR_SUPERFICIE_2,
                          borderwidth=0, rowheight=34, font=(FONTE, -13))
        estilo.configure("Orcamento.Treeview.Heading", background=COR_BOTAO,
                          foreground=COR_TEXTO, relief="flat", borderwidth=0,
                          font=(FONTE, -12, "bold"), padding=(10, 8))
        estilo.map("Orcamento.Treeview", background=[("selected", COR_AZUL)],
                    foreground=[("selected", "#FFFFFF")])
        area = ctk.CTkFrame(lista, fg_color=COR_SUPERFICIE_2, corner_radius=0)
        area.grid(row=1, column=0, sticky="ew", padx=22)
        area.grid_columnconfigure(0, weight=1)
        self.orc_tabela = ttk.Treeview(
            area, columns=("item", "descricao", "valor"), show="headings",
            style="Orcamento.Treeview", height=4, selectmode="browse",
        )
        self.orc_tabela.heading("item", text="Item", anchor="center")
        self.orc_tabela.heading("descricao", text="Serviço / peça", anchor="w")
        self.orc_tabela.heading("valor", text="Valor (R$)", anchor="e")
        self.orc_tabela.column("item", width=55, minwidth=55, stretch=False, anchor="center")
        self.orc_tabela.column("descricao", width=400, minwidth=220, stretch=True)
        self.orc_tabela.column("valor", width=165, minwidth=165, stretch=False, anchor="e")
        self.orc_tabela.grid(row=0, column=0, sticky="nsew")
        sy = ctk.CTkScrollbar(area, orientation="vertical", command=self.orc_tabela.yview)
        sy.grid(row=0, column=1, sticky="ns")
        sx = ctk.CTkScrollbar(area, orientation="horizontal", command=self.orc_tabela.xview)
        sx.grid(row=1, column=0, sticky="ew")
        self.orc_tabela.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.orc_tabela.bind("<Double-1>", self._editar_item_orcamento)
        self.orc_tabela.bind("<Delete>", lambda event: self._remover_item_orcamento())
        controles = ctk.CTkFrame(lista, fg_color="transparent")
        controles.grid(row=0, column=0, sticky="ew", padx=22, pady=(12, 12))
        self.orc_quantidade = ctk.CTkLabel(controles, text="Itens do orçamento",
                                        font=FONTE_SECAO, text_color=COR_TEXTO)
        self.orc_quantidade.pack(side="left")
        self.btn_orc_remover = self._secondary_button(
            controles, "Remover", self._remover_item_orcamento, width=88)
        self.btn_orc_remover.configure(height=32)
        self.btn_orc_remover.pack(side="right")
        self.btn_orc_editar = self._secondary_button(
            controles, "Editar item", self._editar_item_orcamento, width=100)
        self.btn_orc_editar.configure(height=32)
        self.btn_orc_editar.pack(side="right", padx=(0, 8))
        self.btn_orc_cancelar = self._secondary_button(
            controles, "Cancelar edição", self._cancelar_edicao_orcamento, width=132)
        self.btn_orc_cancelar.configure(height=32)
        self.btn_orc_cancelar.pack(side="right", padx=(0, 8))

        extras = self._surface(page)
        extras.grid(row=3, column=0, sticky="ew", pady=(14, 4))
        extras.grid_columnconfigure(0, weight=1)
        self._label(extras, "Observações (opcional)", 0, 0)
        self.orc_observacoes = self._entry(extras, "Condições, prazo ou informações adicionais", 1, 0,
                                          textvariable=self._orc_observacoes_var)
        ctk.CTkLabel(
            extras, text="Rascunho mantido nesta sessão. Gere o PDF antes de sair.",
            font=FONTE_AUXILIAR, text_color=COR_TEXTO_3, anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14))

        # Total e exportação ficam visíveis mesmo quando a página precisa de rolagem.
        acoes = ctk.CTkFrame(self.host, fg_color="transparent", corner_radius=0)
        acoes.grid(row=1, column=0, sticky="ew", padx=22, pady=(16, 0))
        acoes.grid_columnconfigure(0, weight=1)
        self.orc_total = ctk.CTkLabel(acoes, text="Total: R$ 0,00", font=FONTE_SECAO,
                                    text_color=COR_TEXTO, anchor="w")
        self.orc_total.grid(row=0, column=0, sticky="w")
        self._secondary_button(acoes, "Limpar", self._limpar_orcamento, width=95).grid(
            row=0, column=1, padx=(8, 8))
        self.btn_orc_pdf = self._primary_button(
            acoes, "Gerar PDF", self._gerar_pdf_orcamento, width=140,
        )
        self.btn_orc_pdf.grid(row=0, column=2)
        self._atualizar_tabela_orcamento()

    def _atualizar_tabela_orcamento(self):
        self.orc_tabela.delete(*self.orc_tabela.get_children())
        for indice, item in enumerate(self.orc_itens):
            self.orc_tabela.insert("", "end", iid=str(indice), values=(
                indice + 1, item["descricao"], formatar_reais(item["centavos"])))
        total = sum(item["centavos"] for item in self.orc_itens)
        self.orc_total.configure(text=f"Total: {formatar_reais(total)}")
        quantidade = len(self.orc_itens)
        self.orc_quantidade.configure(text=("Itens do orçamento" if not quantidade
                                      else f"Itens do orçamento ({quantidade})"))
        estado = "normal" if quantidade else "disabled"
        self.btn_orc_pdf.configure(state=estado)
        self.btn_orc_remover.configure(state=estado)
        self.btn_orc_editar.configure(state=estado)
        self.btn_orc_cancelar.configure(state="normal" if self._orc_edicao is not None else "disabled")
        self.btn_orc_adicionar.configure(text="Salvar item" if self._orc_edicao is not None else "Adicionar item")

    def _adicionar_item_orcamento(self):
        descricao = self._orc_servico_var.get().strip()
        if not descricao or len(descricao) > 300:
            messagebox.showwarning("Orçamento", "Informe a descrição do item com até 300 caracteres.",
                                   parent=self.janela)
            self.orc_servico.focus_set()
            return
        try:
            centavos = valor_em_centavos(self._orc_valor_var.get())
        except ValueError as erro:
            messagebox.showwarning("Orçamento", str(erro), parent=self.janela)
            self.orc_valor.focus_set()
            return
        item = {"descricao": descricao, "centavos": centavos}
        if self._orc_edicao is None:
            self.orc_itens.append(item)
        else:
            self.orc_itens[self._orc_edicao] = item
        self._cancelar_edicao_orcamento()
        self.orc_tabela.see(str(len(self.orc_itens) - 1))
        self.orc_servico.focus_set()

    def _editar_item_orcamento(self, event=None):
        if event is not None and not self.orc_tabela.identify_row(event.y):
            return
        selecao = self.orc_tabela.selection()
        if not selecao:
            messagebox.showinfo("Orçamento", "Selecione o item que deseja editar.", parent=self.janela)
            return
        if (self._orc_servico_var.get().strip() or self._orc_valor_var.get().strip()) and not messagebox.askyesno(
            "Editar item", "Substituir os dados que estão nos campos de descrição e valor?", parent=self.janela):
            return
        self._orc_edicao = int(selecao[0])
        item = self.orc_itens[self._orc_edicao]
        self._orc_servico_var.set(item["descricao"])
        self._orc_valor_var.set(formatar_reais(item["centavos"]).removeprefix("R$ "))
        self._atualizar_tabela_orcamento()
        self.orc_tabela.selection_set(str(self._orc_edicao))
        self.orc_servico.focus_set()

    def _cancelar_edicao_orcamento(self):
        self._orc_edicao = None
        self._orc_servico_var.set("")
        self._orc_valor_var.set("")
        self._atualizar_tabela_orcamento()

    def _remover_item_orcamento(self):
        selecao = self.orc_tabela.selection()
        if not selecao:
            messagebox.showinfo("Orçamento", "Selecione o item que deseja remover.", parent=self.janela)
            return
        indice = int(selecao[0])
        if not messagebox.askyesno("Remover item", "Remover o item selecionado do orçamento?", parent=self.janela):
            return
        del self.orc_itens[indice]
        if self._orc_edicao == indice:
            self._orc_edicao = None
            self._orc_servico_var.set("")
            self._orc_valor_var.set("")
        elif self._orc_edicao is not None and self._orc_edicao > indice:
            self._orc_edicao -= 1
        self._atualizar_tabela_orcamento()

    def _gerar_pdf_orcamento(self):
        cliente = self._orc_cliente_var.get().strip()
        if not cliente or len(cliente) > 200:
            messagebox.showwarning("Orçamento", "Informe o nome do cliente com até 200 caracteres.", parent=self.janela)
            self.orc_cliente.focus_set()
            return
        if not self.orc_itens:
            messagebox.showwarning("Orçamento", "Adicione pelo menos um item antes de gerar o PDF.", parent=self.janela)
            return
        if self._orc_servico_var.get().strip() or self._orc_valor_var.get().strip():
            messagebox.showwarning("Orçamento", "Há um item nos campos de edição. Adicione ou salve esse item antes de gerar o PDF.", parent=self.janela)
            return
        placa = self._orc_placa_var.get().strip().upper()
        observacoes = self._orc_observacoes_var.get().strip()
        if len(placa) > 20 or len(observacoes) > 2000:
            messagebox.showwarning("Orçamento", "Use até 20 caracteres para a placa e até 2.000 para as observações.", parent=self.janela)
            return
        try:
            import reportlab
        except ImportError:
            messagebox.showerror("Gerar PDF", "Para gerar PDFs, instale o ReportLab no mesmo Python do programa:\n\npython -m pip install reportlab", parent=self.janela)
            return
        nome = re.sub(r"[^\w-]+", "_", placa or cliente, flags=re.UNICODE).strip("_")[:60] or "cliente"
        caminho = filedialog.asksaveasfilename(
            parent=self.janela, title="Salvar orçamento em PDF", defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=f"orcamento_{nome}_{date.today().strftime('%Y-%m-%d')}.pdf",
        )
        if not caminho:
            return
        temporario = None
        try:
            # Só substitui o destino depois da geração completa, preservando um PDF
            # existente se houver falha na escrita ou na montagem do documento.
            with tempfile.NamedTemporaryFile(suffix=".pdf", dir=os.path.dirname(os.path.abspath(caminho)), delete=False) as arquivo:
                temporario = arquivo.name
            gerar_pdf_orcamento(temporario, cliente, placa, self.orc_itens, observacoes, self.nome_usuario)
            os.replace(temporario, caminho)
        except Exception as erro:
            messagebox.showerror("Gerar PDF", f"Não foi possível salvar o PDF.\n\n{erro}", parent=self.janela)
            return
        finally:
            if temporario and os.path.exists(temporario):
                os.remove(temporario)
        messagebox.showinfo("Orçamento", f"PDF gerado com sucesso!\n\n{caminho}", parent=self.janela)

    def _limpar_orcamento(self):
        if self.orc_itens or any(var.get().strip() for var in (
            self._orc_cliente_var, self._orc_placa_var, self._orc_servico_var,
            self._orc_valor_var, self._orc_observacoes_var,
        )):
            if not messagebox.askyesno("Limpar orçamento", "Apagar todos os dados e itens deste orçamento?", parent=self.janela):
                return
        self.orc_itens.clear()
        for var in (self._orc_cliente_var, self._orc_placa_var, self._orc_observacoes_var):
            var.set("")
        self._cancelar_edicao_orcamento()

    # COMPATIBILIDADE COM FUNCOES
    def exibir_clientes(self):
        if not hasattr(self, "tv") or not self.tv.winfo_exists():
            return
        resultado = super().exibir_clientes()
        self._atualizar_quantidade_clientes()
        return resultado

    def limpar_tela(self):
        nomes = [
            "entry_id_cliente",
            "entry_nome",
            "entry_cpf",
            "entry_telefone",
            "entry_endereco",
            "entry_placa",
            "entry_marca",
            "entry_modelo",
            "entry_ano",
        ]
        for nome in nomes:
            campo = getattr(self, nome, None)
            if campo is not None and campo.winfo_exists():
                campo.delete(0, "end")
        self.id_veiculo = None

    def limpar_os(self):
        for nome in ("entry_num_os", "entry_os_placa", "entry_valor"):
            campo = getattr(self, nome, None)
            if campo is not None and campo.winfo_exists():
                campo.delete(0, "end")

        descricao = getattr(self, "entry_descricao", None)
        if descricao is not None and descricao.winfo_exists():
            descricao.delete("1.0", "end")

    def logout(self):
        if not messagebox.askyesno("Sair", "Deseja encerrar a sessão atual?"):
            return

        for widget in self.janela.winfo_children():
            widget.destroy()
        Login(self.janela)



# EXECUÇÃO

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    preparar_usuarios()

    janela = ctk.CTk()
    Login(janela)
    janela.mainloop()


if __name__ == "__main__":
    main()

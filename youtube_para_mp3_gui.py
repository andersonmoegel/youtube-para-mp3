#!/usr/bin/env python3
"""
Baixador de video do YouTube -> MP3 (interface grafica, visual escuro/futurista)

Este arquivo e compilado em um unico executavel (Baixador de MP3.exe) atraves
do "gerar_executavel.bat". O executavel final ja inclui o Python e todas as
bibliotecas - a pessoa que for usar so precisa dar dois cliques nele.

Requisitos para GERAR o executavel (nao para usa-lo):
    pip install "yt-dlp[default]" pillow customtkinter pyinstaller

Ao ser aberto, o proprio programa verifica e instala sozinho (em segundo
plano, com uma tela de carregamento) duas ferramentas externas que o YouTube
exige para os downloads funcionarem: ffmpeg e Deno.

Aviso: baixe apenas conteudo que voce tem direito de baixar (seu proprio
video, dominio publico, licenca Creative Commons, etc.). Respeite os
Termos de Servico do YouTube e leis de direitos autorais.
"""

import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from tkinter import filedialog, messagebox


def _erro_fatal(mensagem: str) -> None:
    """Mostra um erro visivel mesmo sem console (usa a API nativa do Windows)."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0, mensagem, "Baixador de MP3 - Erro", 0x10
        )
    except Exception:
        pass
    sys.exit(1)


try:
    import customtkinter as ctk
except ImportError:
    _erro_fatal(
        "O programa nao foi instalado corretamente.\n\n"
        "Gere o executavel novamente ou reinstale o aplicativo."
    )
    raise

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from PIL import Image
except ImportError:
    Image = None


# ---------------------------------------------------------------------------
# Paleta "futurista" escura
# ---------------------------------------------------------------------------
BG = "#0a0e17"
BG_CARD = "#121826"
BORDER = "#1f2a3d"
ACCENT = "#00e5ff"      # ciano neon
ACCENT2 = "#b026ff"     # roxo/magenta neon
ACCENT_DIM = "#0891a8"
TEXT_PRIMARY = "#e6f1ff"
TEXT_SECONDARY = "#7b8aa3"
SUCCESS = "#00ffa3"
ERRO_COR = "#ff4d6d"
LOG_BG = "#050810"

LARGURA_PAINEL = 640

PASTA_PADRAO = os.path.join(os.path.expanduser("~"), "Downloads", "mp3_youtube")
OEMBED_URL = "https://www.youtube.com/oembed?url={}&format=json"
REGEX_YOUTUBE = re.compile(
    r"(youtube\.com/watch\?v=|youtube\.com/shorts/|youtu\.be/|youtube\.com/live/)",
    re.IGNORECASE,
)

CREATE_NO_WINDOW = 0x08000000  # evita qualquer flash de janela preta


# ---------------------------------------------------------------------------
# Preparo automatico de dependencias externas (ffmpeg, Deno)
# ---------------------------------------------------------------------------

def _rodar_oculto(cmd, timeout=300):
    """Executa um comando sem mostrar nenhuma janela de console."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception:
        return None


def _atualizar_path_processo():
    """Le o PATH mais recente do registro do Windows para o processo atual
    conseguir enxergar programas instalados agora mesmo (sem reiniciar)."""
    if sys.platform != "win32":
        return
    try:
        import winreg

        partes = []
        for hive, subkey in (
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ),
        ):
            try:
                with winreg.OpenKey(hive, subkey) as chave:
                    valor, _ = winreg.QueryValueEx(chave, "Path")
                    partes.append(valor)
            except OSError:
                pass
        partes.append(os.path.join(os.path.expanduser("~"), ".deno", "bin"))
        if partes:
            os.environ["PATH"] = ";".join(partes) + ";" + os.environ.get("PATH", "")
    except Exception:
        pass


def _persistir_path_usuario(nova_pasta):
    """Adiciona uma pasta ao PATH do usuario, para as proximas vezes que o
    programa abrir nao precisar baixar tudo de novo."""
    if sys.platform != "win32":
        return
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS
        ) as chave:
            try:
                atual, _ = winreg.QueryValueEx(chave, "Path")
            except FileNotFoundError:
                atual = ""
            if nova_pasta.lower() not in atual.lower():
                novo = (atual + ";" + nova_pasta) if atual else nova_pasta
                winreg.SetValueEx(chave, "Path", 0, winreg.REG_EXPAND_SZ, novo)
    except Exception:
        pass


def _garantir_ffmpeg():
    """Garante que o ffmpeg exista, instalando automaticamente se preciso."""
    if shutil.which("ffmpeg"):
        return True

    if shutil.which("winget"):
        _rodar_oculto(
            [
                "winget", "install", "-e", "--id", "Gyan.FFmpeg",
                "--scope", "user", "--silent",
                "--accept-package-agreements", "--accept-source-agreements",
            ]
        )
        _atualizar_path_processo()
        if shutil.which("ffmpeg"):
            return True

    # alternativa: baixa uma versao portatil e usa direto dessa pasta
    try:
        pasta_apps = os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "BaixadorMP3", "ffmpeg"
        )
        os.makedirs(pasta_apps, exist_ok=True)
        zip_path = os.path.join(pasta_apps, "ffmpeg.zip")
        urllib.request.urlretrieve(
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            zip_path,
        )
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(pasta_apps)
        os.remove(zip_path)
        for nome in os.listdir(pasta_apps):
            candidato = os.path.join(pasta_apps, nome, "bin")
            if os.path.isfile(os.path.join(candidato, "ffmpeg.exe")):
                os.environ["PATH"] = candidato + ";" + os.environ.get("PATH", "")
                _persistir_path_usuario(candidato)
                return True
    except Exception:
        pass
    return shutil.which("ffmpeg") is not None


def _garantir_deno():
    """Garante que o Deno exista (necessario para o YouTube liberar os
    downloads), instalando automaticamente se preciso."""
    if shutil.which("deno"):
        return True

    if shutil.which("winget"):
        _rodar_oculto(
            [
                "winget", "install", "-e", "--id", "DenoLand.Deno",
                "--scope", "user", "--silent",
                "--accept-package-agreements", "--accept-source-agreements",
            ]
        )
        _atualizar_path_processo()
        if shutil.which("deno"):
            return True

    _rodar_oculto(
        [
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
            "irm https://deno.land/install.ps1 | iex",
        ]
    )
    _atualizar_path_processo()
    return shutil.which("deno") is not None


# ---------------------------------------------------------------------------
# Janela / visual
# ---------------------------------------------------------------------------

def _titulo_janela_escuro(root):
    """Deixa a barra de titulo do Windows escura (Windows 10 1809+/11)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        root.update()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        valor = ctypes.c_int(1)
        for atributo in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (novo/antigo)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor)
            )
    except Exception:
        pass


def _maximizar(root):
    """Maximiza a janela (estado nativo do Windows), mantendo a barra de
    titulo, os botoes de minimizar/restaurar/fechar e a barra de tarefas
    visiveis. Isto NAO e tela cheia (sem decoracao)."""

    def _aplicar():
        try:
            root.state("zoomed")  # Windows e algumas builds de Tk no Linux
            return
        except Exception:
            pass
        try:
            root.attributes("-zoomed", True)  # Linux (algumas WMs)
        except Exception:
            pass

    # adiar um instante ajuda o "zoomed" a "pegar" de forma confiavel,
    # pois a janela precisa estar totalmente criada/mapeada primeiro
    root.update_idletasks()
    root.after(10, _aplicar)


def _centralizar(root, largura, altura):
    root.update_idletasks()
    x = (root.winfo_screenwidth() - largura) // 2
    y = (root.winfo_screenheight() - altura) // 2
    root.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")


# ---------------------------------------------------------------------------
# Tela de carregamento inicial (linguagem simples, sem termos tecnicos)
# ---------------------------------------------------------------------------

class TelaCarregamento:
    MENSAGENS = ["Preparando tudo...", "Quase la...", "So mais um instante..."]

    def __init__(self, root, ao_concluir):
        self.root = root
        self.ao_concluir = ao_concluir
        self.fila = queue.Queue()
        self._indice_msg = 0

        self.root.title("Baixador de MP3")
        self.root.configure(fg_color=BG)
        self.root.resizable(False, False)
        _centralizar(self.root, 420, 280)
        _titulo_janela_escuro(self.root)

        cartao = ctk.CTkFrame(
            self.root,
            fg_color=BG_CARD,
            corner_radius=20,
            border_width=1,
            border_color=BORDER,
        )
        cartao.pack(fill="both", expand=True, padx=16, pady=16)

        fonte_logo = ctk.CTkFont(family="Segoe UI", size=30, weight="bold")
        fonte_texto = ctk.CTkFont(family="Segoe UI", size=13)

        frame_logo = ctk.CTkFrame(cartao, fg_color="transparent")
        frame_logo.pack(pady=(40, 6))
        ctk.CTkLabel(frame_logo, text="YT", font=fonte_logo, text_color=ACCENT2).pack(
            side="left"
        )
        ctk.CTkLabel(
            frame_logo, text=" ⚡ ", font=fonte_logo, text_color=TEXT_SECONDARY
        ).pack(side="left")
        ctk.CTkLabel(frame_logo, text="MP3", font=fonte_logo, text_color=ACCENT).pack(
            side="left"
        )

        self.label_status = ctk.CTkLabel(
            cartao, text=self.MENSAGENS[0], font=fonte_texto, text_color=TEXT_PRIMARY
        )
        self.label_status.pack(pady=(6, 22))

        self.barra = ctk.CTkProgressBar(
            cartao,
            width=260,
            height=8,
            corner_radius=4,
            fg_color=BORDER,
            progress_color=ACCENT,
            mode="indeterminate",
        )
        self.barra.pack()
        self.barra.start()

        threading.Thread(target=self._preparar, daemon=True).start()
        self.root.after(120, self._trocar_mensagem)
        self.root.after(150, self._checar_fila)

    def _trocar_mensagem(self):
        self._indice_msg = (self._indice_msg + 1) % len(self.MENSAGENS)
        try:
            self.label_status.configure(text=self.MENSAGENS[self._indice_msg])
        except Exception:
            return
        self.root.after(1800, self._trocar_mensagem)

    def _preparar(self):
        inicio = time.time()
        try:
            _garantir_ffmpeg()
            _garantir_deno()
        except Exception:
            pass
        # duracao minima para a tela nao "piscar" e parecer instantanea demais
        restante = 1.1 - (time.time() - inicio)
        if restante > 0:
            time.sleep(restante)
        self.fila.put("pronto")

    def _checar_fila(self):
        try:
            self.fila.get_nowait()
            self.barra.stop()
            self.ao_concluir()
            return
        except queue.Empty:
            pass
        self.root.after(150, self._checar_fila)


class BaixadorApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Baixador de MP3")
        # a tela de carregamento deixa a janela travada em tamanho fixo;
        # aqui ela precisa voltar a ser redimensionavel/maximizavel de verdade
        self.root.resizable(True, True)
        self.root.geometry("1024x768")
        self.root.minsize(540, 640)
        self.root.configure(fg_color=BG)
        _titulo_janela_escuro(self.root)
        _maximizar(self.root)

        self.pasta_saida = PASTA_PADRAO
        self.fila = queue.Queue()
        self.thumb_img = None
        self.baixando = False

        self.fonte_titulo = ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
        self.fonte_subtitulo = ctk.CTkFont(family="Segoe UI", size=12)
        self.fonte_label = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        self.fonte_texto = ctk.CTkFont(family="Segoe UI", size=12)
        self.fonte_botao = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.fonte_log = ctk.CTkFont(family="Consolas", size=11)

        self._montar_layout()
        self._verificar_dependencias()
        self.root.after(100, self._processar_fila)

    # ---------- layout ----------

    def _montar_layout(self):
        # painel central com largura fixa, para nao esticar em telas grandes
        # (customtkinter exige que width/height sejam passados no construtor,
        # nao no place())
        self.container = ctk.CTkFrame(
            self.root, fg_color="transparent", width=LARGURA_PAINEL
        )
        self.container.pack_propagate(False)
        self.container.place(relx=0.5, rely=0.03, anchor="n", relheight=0.94)

        # --- cabecalho ---
        frame_topo = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_topo.pack(pady=(2, 2))

        frame_marca = ctk.CTkFrame(frame_topo, fg_color="transparent")
        frame_marca.pack()
        ctk.CTkLabel(
            frame_marca, text="YT", font=self.fonte_titulo, text_color=ACCENT2
        ).pack(side="left")
        ctk.CTkLabel(
            frame_marca,
            text=" ⚡ ",
            font=self.fonte_titulo,
            text_color=TEXT_SECONDARY,
        ).pack(side="left")
        ctk.CTkLabel(
            frame_marca, text="MP3", font=self.fonte_titulo, text_color=ACCENT
        ).pack(side="left")

        ctk.CTkLabel(
            self.container,
            text="Cole o link, pre-visualize e baixe em segundos.",
            font=self.fonte_subtitulo,
            text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 18))

        # --- cartao: link ---
        card_link = self._novo_cartao()
        card_link.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card_link,
            text="LINK DO YOUTUBE",
            font=self.fonte_label,
            text_color=ACCENT,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        frame_entry = ctk.CTkFrame(card_link, fg_color="transparent")
        frame_entry.pack(fill="x", padx=18, pady=(0, 18))

        self.entry_url = ctk.CTkEntry(
            frame_entry,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=self.fonte_texto,
            fg_color=BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            corner_radius=10,
            height=40,
        )
        self.entry_url.pack(side="left", fill="x", expand=True)
        self.entry_url.bind("<Return>", lambda e: self._pre_visualizar())
        # pre-visualiza sozinho assim que um link e colado com Ctrl+V/menu
        self.entry_url.bind("<<Paste>>", self._ao_colar_no_campo)

        ctk.CTkButton(
            frame_entry,
            text="Colar",
            width=70,
            height=40,
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            border_color=BORDER,
            hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=self.fonte_texto,
            command=self._colar,
        ).pack(side="left", padx=(8, 0))

        # --- cartao: preview ---
        card_preview = self._novo_cartao()
        card_preview.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card_preview,
            text="PRE-VISUALIZACAO",
            font=self.fonte_label,
            text_color=ACCENT,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        frame_preview = ctk.CTkFrame(card_preview, fg_color="transparent")
        frame_preview.pack(fill="x", padx=18, pady=(0, 18))

        self.frame_thumb = ctk.CTkFrame(
            frame_preview,
            width=160,
            height=120,
            corner_radius=10,
            fg_color=BG,
            border_width=1,
            border_color=BORDER,
        )
        self.frame_thumb.pack(side="left")
        self.frame_thumb.pack_propagate(False)

        self.label_thumb = ctk.CTkLabel(
            self.frame_thumb,
            text="sem imagem",
            font=self.fonte_subtitulo,
            text_color=TEXT_SECONDARY,
        )
        self.label_thumb.pack(expand=True)

        frame_info = ctk.CTkFrame(frame_preview, fg_color="transparent")
        frame_info.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self.label_titulo = ctk.CTkLabel(
            frame_info,
            text="Titulo: -",
            font=self.fonte_texto,
            text_color=TEXT_PRIMARY,
            justify="left",
            anchor="w",
            wraplength=360,
        )
        self.label_titulo.pack(anchor="w", fill="x", pady=(0, 6))

        self.label_canal = ctk.CTkLabel(
            frame_info,
            text="Canal: -",
            font=self.fonte_texto,
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.label_canal.pack(anchor="w")

        # --- cartao: pasta + acao ---
        card_acao = self._novo_cartao()
        card_acao.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card_acao,
            text="SALVAR EM",
            font=self.fonte_label,
            text_color=ACCENT,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        frame_pasta = ctk.CTkFrame(card_acao, fg_color="transparent")
        frame_pasta.pack(fill="x", padx=18)

        self.label_pasta = ctk.CTkLabel(
            frame_pasta,
            text=self.pasta_saida,
            font=self.fonte_texto,
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.label_pasta.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            frame_pasta,
            text="Alterar",
            width=90,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=BORDER,
            hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=self.fonte_texto,
            command=self._alterar_pasta,
        ).pack(side="right")

        self.botao_baixar = ctk.CTkButton(
            card_acao,
            text="⬇  BAIXAR MP3",
            height=50,
            corner_radius=25,
            fg_color=ACCENT,
            hover_color=ACCENT_DIM,
            text_color="#001018",
            font=self.fonte_botao,
            command=self._iniciar_download,
        )
        self.botao_baixar.pack(fill="x", padx=18, pady=18)

        self.progresso = ctk.CTkProgressBar(
            card_acao,
            height=10,
            corner_radius=5,
            fg_color=BORDER,
            progress_color=ACCENT,
        )
        self.progresso.set(0)
        self.progresso.pack(fill="x", padx=18, pady=(0, 6))

        self.label_status = ctk.CTkLabel(
            card_acao,
            text="Pronto.",
            font=self.fonte_subtitulo,
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.label_status.pack(anchor="w", padx=18, pady=(0, 16))

        # --- cartao: log ---
        card_log = self._novo_cartao()
        card_log.pack(fill="both", expand=True, pady=(8, 4))

        frame_log_topo = ctk.CTkFrame(card_log, fg_color="transparent")
        frame_log_topo.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            frame_log_topo,
            text="HISTORICO",
            font=self.fonte_label,
            text_color=ACCENT,
        ).pack(side="left")

        ctk.CTkButton(
            frame_log_topo,
            text="Abrir pasta",
            width=100,
            height=26,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=BORDER,
            hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=self.fonte_subtitulo,
            command=self._abrir_pasta,
        ).pack(side="right")

        self.texto_log = ctk.CTkTextbox(
            card_log,
            fg_color=LOG_BG,
            text_color=ACCENT,
            font=self.fonte_log,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
            state="disabled",
        )
        self.texto_log.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def _novo_cartao(self):
        return ctk.CTkFrame(
            self.container,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )

    # ---------- checagens iniciais ----------

    def _verificar_dependencias(self):
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        deno_ok = shutil.which("deno") is not None
        self._log(
            "Preparo: conversor de audio "
            + ("OK" if ffmpeg_ok else "NAO encontrado")
            + " | liberacao de video "
            + ("OK" if deno_ok else "NAO encontrada")
        )
        if not ffmpeg_ok:
            self._log(
                "Aviso: nao foi possivel preparar a conversao para MP3 "
                "automaticamente. Feche e abra o programa novamente."
            )
        if not deno_ok:
            self._log(
                "Aviso: alguns videos podem falhar ao baixar. Feche e abra o "
                "programa novamente para tentar preparar tudo de novo."
            )

    # ---------- acoes da UI ----------

    def _colar(self):
        try:
            texto = self.root.clipboard_get()
        except tk.TclError:
            texto = ""
        if texto:
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, texto.strip())
            self._pre_visualizar(silencioso=True)

    def _ao_colar_no_campo(self, event=None):
        # o texto colado (Ctrl+V/menu de contexto) ainda nao esta no campo
        # no momento deste evento, entao espera um instante antes de checar
        self.root.after(50, lambda: self._pre_visualizar(silencioso=True))

    def _alterar_pasta(self):
        nova = filedialog.askdirectory(initialdir=self.pasta_saida)
        if nova:
            self.pasta_saida = nova
            self.label_pasta.configure(text=self.pasta_saida)

    def _abrir_pasta(self):
        os.makedirs(self.pasta_saida, exist_ok=True)
        try:
            os.startfile(self.pasta_saida)  # Windows
        except AttributeError:
            messagebox.showinfo("Pasta de downloads", self.pasta_saida)

    def _log(self, mensagem):
        self.texto_log.configure(state="normal")
        self.texto_log.insert("end", mensagem + "\n")
        try:
            self.texto_log.see("end")
        except Exception:
            pass
        self.texto_log.configure(state="disabled")

    def _url_valida(self, url):
        return bool(url) and REGEX_YOUTUBE.search(url) is not None

    def _limpar_para_novo_download(self):
        """Reseta os campos (link, previa, progresso) para um novo download,
        mantendo o historico visivel."""
        self.entry_url.delete(0, "end")
        self.label_titulo.configure(text="Titulo: -")
        self.label_canal.configure(text="Canal: -")
        self.label_thumb.configure(image=None, text="sem imagem")
        self.thumb_img = None
        self.progresso.set(0)
        self.label_status.configure(text="Pronto.", text_color=TEXT_SECONDARY)

    # ---------- pre-visualizacao (API publica oEmbed do YouTube) ----------

    def _pre_visualizar(self, silencioso=False):
        url = self.entry_url.get().strip()
        if not self._url_valida(url):
            if not silencioso:
                messagebox.showwarning(
                    "Link invalido", "Cole um link valido do YouTube antes de pre-visualizar."
                )
            return

        self.label_titulo.configure(text="Titulo: buscando...")
        self.label_canal.configure(text="Canal: buscando...")
        self.label_thumb.configure(image=None, text="carregando...")

        threading.Thread(target=self._buscar_preview, args=(url,), daemon=True).start()

    def _buscar_preview(self, url):
        try:
            api_url = OEMBED_URL.format(urllib.parse.quote(url, safe=""))
            with urllib.request.urlopen(api_url, timeout=10) as resp:
                dados = json.loads(resp.read().decode("utf-8"))

            titulo = dados.get("title", "(sem titulo)")
            canal = dados.get("author_name", "(desconhecido)")
            thumb_url = dados.get("thumbnail_url")

            ctk_img = None
            if thumb_url and Image is not None:
                with urllib.request.urlopen(thumb_url, timeout=10) as resp_img:
                    dados_img = resp_img.read()
                imagem = Image.open(io.BytesIO(dados_img))
                imagem.thumbnail((150, 110))
                ctk_img = ctk.CTkImage(
                    light_image=imagem, dark_image=imagem, size=imagem.size
                )

            self.fila.put(("preview_ok", titulo, canal, ctk_img))
        except urllib.error.HTTPError:
            self.fila.put(
                (
                    "preview_erro",
                    "Nao foi possivel pre-visualizar este link (video privado, "
                    "indisponivel ou invalido).",
                )
            )
        except Exception as e:
            self.fila.put(("preview_erro", f"Erro ao pre-visualizar: {e}"))

    # ---------- download ----------

    def _iniciar_download(self):
        if self.baixando:
            return

        url = self.entry_url.get().strip()
        if not self._url_valida(url):
            messagebox.showwarning(
                "Link invalido", "Cole um link valido do YouTube antes de baixar."
            )
            return
        if yt_dlp is None:
            messagebox.showerror(
                "Nao disponivel",
                "O programa nao foi instalado corretamente. Gere o executavel "
                "novamente.",
            )
            return

        self.baixando = True
        self.botao_baixar.configure(state="disabled", text="Baixando...")
        self.progresso.set(0)
        self.label_status.configure(text="Iniciando download...")
        self._log(f"Baixando: {url}")

        threading.Thread(target=self._baixar_thread, args=(url,), daemon=True).start()

    def _baixar_thread(self, url):
        os.makedirs(self.pasta_saida, exist_ok=True)

        def progress_hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                baixado = d.get("downloaded_bytes", 0)
                percent = (baixado / total * 100) if total else 0
                velocidade = (d.get("_speed_str") or "").strip()
                self.fila.put(("progresso", percent, f"Baixando... {velocidade}"))
            elif d.get("status") == "finished":
                self.fila.put(("progresso", 100, "Convertendo para MP3..."))

        opcoes = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.pasta_saida, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
            # se os arquivos que resolvem o desafio do YouTube (EJS) nao
            # vieram empacotados corretamente, isso permite baixa-los na
            # hora do GitHub como reforco (nao deveria ser necessario, mas
            # evita falha caso o empacotamento do .exe fique incompleto)
            "remote_components": ["ejs:github"],
        }

        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                ydl.download([url])
            self.fila.put(("download_ok", self.pasta_saida))
            return
        except Exception as e:
            msg = str(e)

        bloqueado = "403" in msg or "Forbidden" in msg

        # se o bloqueio aconteceu e o componente de liberacao de video nao
        # esta presente, tenta prepara-lo agora mesmo e baixar de novo uma vez
        if bloqueado and shutil.which("deno") is None:
            self.fila.put(("progresso", 0, "Preparando novamente..."))
            _garantir_deno()
            if shutil.which("deno"):
                try:
                    with yt_dlp.YoutubeDL(opcoes) as ydl:
                        ydl.download([url])
                    self.fila.put(("download_ok", self.pasta_saida))
                    return
                except Exception as e2:
                    msg = str(e2)
                    bloqueado = "403" in msg or "Forbidden" in msg

        if bloqueado:
            if shutil.which("deno") is not None:
                msg = (
                    "O YouTube bloqueou este video agora (pode ser temporario "
                    "ou so deste video especifico).\n\n"
                    "Tente novamente em alguns minutos, ou teste com outro "
                    "link para confirmar se o problema e so deste video.\n\n"
                    "Detalhes tecnicos: " + msg
                )
            else:
                msg = (
                    "Nao foi possivel preparar um componente necessario para "
                    "baixar do YouTube (verifique sua conexao com a "
                    "internet). Feche o programa e abra de novo para tentar "
                    "preparar tudo outra vez.\n\n"
                    "Detalhes tecnicos: " + msg
                )

        self.fila.put(("download_erro", msg))

    # ---------- fila de eventos (thread -> UI) ----------

    def _processar_fila(self):
        try:
            while True:
                item = self.fila.get_nowait()
                tipo = item[0]

                if tipo == "preview_ok":
                    _, titulo, canal, ctk_img = item
                    self.label_titulo.configure(text=f"Titulo: {titulo}")
                    self.label_canal.configure(text=f"Canal: {canal}")
                    if ctk_img is not None:
                        self.thumb_img = ctk_img
                        self.label_thumb.configure(image=self.thumb_img, text="")
                    else:
                        self.label_thumb.configure(image=None, text="sem imagem")

                elif tipo == "preview_erro":
                    _, msg = item
                    self.label_titulo.configure(text="Titulo: -")
                    self.label_canal.configure(text="Canal: -")
                    self.label_thumb.configure(image=None, text="sem imagem")
                    self._log(msg)

                elif tipo == "progresso":
                    _, percent, status = item
                    self.progresso.set(max(0.0, min(1.0, percent / 100)))
                    self.label_status.configure(text=status)

                elif tipo == "download_ok":
                    _, pasta = item
                    self.progresso.set(1.0)
                    self.label_status.configure(text="Concluido!", text_color=SUCCESS)
                    self._log(f"Concluido! Arquivo salvo em: {pasta}")
                    self.botao_baixar.configure(state="normal", text="⬇  BAIXAR MP3")
                    self.baixando = False
                    messagebox.showinfo(
                        "Download concluido",
                        f"O MP3 foi baixado com sucesso!\n\nSalvo em:\n{pasta}",
                    )
                    self._limpar_para_novo_download()

                elif tipo == "download_erro":
                    _, msg = item
                    self.label_status.configure(text="Erro no download.", text_color=ERRO_COR)
                    self._log(f"Erro: {msg}")
                    messagebox.showerror("Erro ao baixar", msg)
                    self.botao_baixar.configure(state="normal", text="⬇  BAIXAR MP3")
                    self.baixando = False

        except queue.Empty:
            pass

        self.root.after(100, self._processar_fila)


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()

    def _abrir_app_principal():
        for widget in root.winfo_children():
            widget.destroy()
        BaixadorApp(root)

    TelaCarregamento(root, _abrir_app_principal)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _erro_fatal(
            "O programa encontrou um erro inesperado:\n\n" + traceback.format_exc()
        )

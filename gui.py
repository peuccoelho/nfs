import asyncio
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from playwright._impl._driver import compute_driver_executable

from config import Config
from portal import PortalNFSE
from utils import get_logger, setup_logging

logger = get_logger(__name__)
setup_logging()

# --- Corrige caminho dos browsers do Playwright no PyInstaller ---
if getattr(sys, "frozen", False):
    # Quando executavel .exe, aponta pro diretorio de dados local do usuario
    pasta_browsers = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"
else:
    pasta_browsers = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pasta_browsers)
# ---------------------------------------------------------------


def _caminho_chromium() -> Path | None:
    """Retorna o caminho do chrome.exe do Playwright, ou None se nao existir."""
    if not pasta_browsers.exists():
        return None
    # Procura por cromio-*/chrome-win64/chrome.exe
    for pasta in pasta_browsers.iterdir():
        if pasta.name.startswith("chromium-"):
            chrome = pasta / "chrome-win64" / "chrome.exe"
            if chrome.exists():
                return chrome
    return None


def verificar_playwright() -> bool:
    """Verifica se o Chromium do Playwright esta instalado (por arquivo)."""
    return _caminho_chromium() is not None


def _cmd_playwright() -> list[str]:
    """Retorna o comando para executar o Playwright CLI (funciona no .exe)."""
    node, cli = compute_driver_executable()
    return [str(node), str(cli)]


def instalar_playwright(silencioso: bool = False) -> bool:
    """Instala o Chromium do Playwright.

    Args:
        silencioso: Se True, nao mostra janela de progresso (usado pelo instalador).

    Returns:
        True se instalou com sucesso.
    """
    import threading

    cmd = _cmd_playwright() + ["install", "chromium"]
    env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(pasta_browsers)}

    if silencioso:
        try:
            subprocess.run(cmd, check=True, capture_output=True, env=env)
            return _caminho_chromium() is not None
        except Exception:
            return False

    # --- Modo com GUI (janela de progresso) ---
    top = tk.Toplevel(root)
    top.title("Instalando Chromium...")
    top.geometry("520x280")
    top.resizable(False, False)
    top.transient(root)
    top.grab_set()

    tk.Label(top, text="Baixando Chromium (~180 MB)...", font=("Arial", 10, "bold")).pack(pady=(8, 2))
    tk.Label(top, text="Isso pode levar alguns minutos.", foreground="gray", font=("Arial", 8)).pack()

    barra = ttk.Progressbar(top, mode="indeterminate", length=460)
    barra.pack(pady=8)
    barra.start()

    texto = tk.Text(top, height=10, width=60, state="disabled", wrap="word")
    texto.pack(padx=10, pady=5)
    scroll = ttk.Scrollbar(top, orient="vertical", command=texto.yview)
    scroll.pack(side="right", fill="y")
    texto.config(yscrollcommand=scroll.set)

    status_label = tk.Label(top, text="Iniciando...", foreground="blue", font=("Arial", 8))
    status_label.pack(pady=4)

    resultado = {"ok": False}
    fila_log = []

    def processar_fila():
        while fila_log:
            msg, tipo = fila_log.pop(0)
            if tipo == "log":
                texto.config(state="normal")
                texto.insert("end", msg + "\n")
                texto.see("end")
                texto.config(state="disabled")
            elif tipo == "status":
                status_label.config(text=msg)
        root.after(100, processar_fila)

    root.after(100, processar_fila)

    def log(msg):
        fila_log.append((msg, "log"))

    def set_status(msg):
        fila_log.append((msg, "status"))

    def instalacao():
        log("Preparando ambiente...")
        log(f"Comando: {' '.join(cmd)}")
        log("Baixando e instalando Chromium...")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                env=env,
            )
            for linha in proc.stdout:
                linha = linha.strip()
                if linha:
                    log(linha)
                    if any(p in linha.lower() for p in ["download", "progress", "%"]):
                        set_status(linha)

            proc.wait()
            if proc.returncode == 0 and _caminho_chromium() is not None:
                log("")
                log("Instalacao concluida com sucesso!")
                resultado["ok"] = True
            else:
                log(f"Erro: codigo {proc.returncode}")
        except Exception as e:
            log(f"Falha: {e}")

        set_status("Concluido!" if resultado["ok"] else "Erro!")
        top.after(1000, top.destroy)

    threading.Thread(target=instalacao, daemon=True).start()
    root.wait_window(top)

    if resultado["ok"]:
        messagebox.showinfo("Sucesso", "Chromium instalado com sucesso!")
        return True
    else:
        messagebox.showerror("Erro", "Falha ao instalar Chromium.\nVeja o log para mais detalhes.")
        return False


def primeiro_acesso() -> bool:
    """Tela de primeiro acesso: instalar Playwright se necessario."""
    if verificar_playwright():
        return True

    resposta = messagebox.askyesno(
        "Primeiro acesso",
        "O Chromium (navegador necessario) ainda nao foi instalado.\n"
        "Deseja instalar agora?",
    )
    if resposta:
        return instalar_playwright()
    return False


def rodar():
    """Callback do botao: le mes/ano e inicia a exportacao em thread separada."""
    if not primeiro_acesso():
        return

    try:
        mes = int(combo_mes.get())
        ano = int(combo_ano.get())
    except ValueError:
        messagebox.showerror("Erro", "Selecione mes e ano validos")
        return

    config = Config()
    config.mes = mes
    config.ano = ano

    if not config.usuario or not config.senha:
        messagebox.showerror(
            "Erro", "Preencha o arquivo .env com USUARIO e SENHA"
        )
        return

    btn.config(state="disabled", text="Executando...")
    status.config(text="Processando...")
    root.update()

    import threading

    def executar_async():
        async def tarefa():
            portal = PortalNFSE(config)
            try:
                await portal.iniciar()
                await portal.navegar_para_nota_fiscal()
                await portal.executar_consulta()
                logger.info("Exportacao concluida com sucesso!")
                root.after(0, lambda: status.config(text="Concluido!"))
                root.after(0, lambda: messagebox.showinfo("Sucesso", "Exportacao finalizada!"))
            except Exception as e:
                logger.error("Erro: %s", e)
                root.after(0, lambda: status.config(text="Erro! Veja o log"))
                root.after(0, lambda: messagebox.showerror("Erro", str(e)))
            finally:
                await portal.fechar()
                root.after(0, lambda: btn.config(state="normal", text="Iniciar"))

        asyncio.run(tarefa())

    threading.Thread(target=executar_async, daemon=True).start()


def abrir_env():
    """Abre o arquivo .env no bloco de notas sem travar a interface."""
    # Quando .exe, o .env fica na pasta do executavel, nao no _MEI temp
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    env_path = base / ".env"

    if not env_path.exists():
        example = base / ".env.example"
        if example.exists():
            env_path.write_text(example.read_text())
        else:
            env_path.write_text("USUARIO=\nSENHA=\n")

    subprocess.Popen(["notepad.exe", str(env_path)])


# --- Interface ---
root = tk.Tk()
root.title("Exportador NFS-e - Camacari")
root.geometry("360x280")
root.resizable(False, False)

tk.Label(
    root, text="Exportador de XMLs NFS-e", font=("Arial", 12, "bold")
).pack(pady=(12, 4))

tk.Label(
    root, text="Prefeitura de Camacari", font=("Arial", 9), foreground="gray"
).pack()

frame = ttk.Frame(root, padding=10)
frame.pack()

ttk.Label(frame, text="Mes:").grid(row=0, column=0, sticky="w", pady=5)
combo_mes = ttk.Combobox(
    frame, values=[f"{m:02d}" for m in range(1, 13)], width=8, state="readonly"
)
combo_mes.grid(row=0, column=1, pady=5)
combo_mes.set("05")

ttk.Label(frame, text="Ano:").grid(row=1, column=0, sticky="w", pady=5)
combo_ano = ttk.Combobox(
    frame, values=[str(a) for a in range(2024, 2031)], width=8, state="readonly"
)
combo_ano.grid(row=1, column=1, pady=5)
combo_ano.set("2026")

btn = ttk.Button(root, text="Iniciar", command=rodar)
btn.pack(pady=(6, 2))

ttk.Button(root, text="Configurar .env", command=abrir_env).pack(pady=2)

status = ttk.Label(root, text="Pronto", foreground="gray")
status.pack(pady=(6, 0))

# Exibe caminho dos downloads
_base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
caminho_downloads = _base / "downloads"
ttk.Label(root, text=str(caminho_downloads), foreground="gray", font=("Arial", 7)).pack(pady=(2, 0))
ttk.Button(root, text="Abrir pasta de downloads", command=lambda: subprocess.Popen(["explorer", str(caminho_downloads)])).pack(pady=(2, 4))

# Se chamado com --install-playwright, instala em modo silencioso e sai
if "--install-playwright" in sys.argv:
    root.withdraw()  # Esconde a janela principal
    ok = instalar_playwright(silencioso=True)
    sys.exit(0 if ok else 1)

root.mainloop()

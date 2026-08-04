#! /usr/bin/env python3
"""Interface grafica (Tkinter) da automacao de faturamento de OS no Omie.

Executa a automacao em thread separada. A janela de codigo 2FA e aberta
automaticamente pela automacao quando necessaria.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from omie.automation.runner import AutomationRunner
from omie.config import Credentials, Settings
from omie.services.logger import get_logger, setup_logging
from omie.services.report import ReportGenerator

logger = get_logger(__name__)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def rodar() -> None:
    """Callback do botao: inicia a automacao em thread separada."""
    try:
        settings = Settings.load()
        credentials = Credentials.load()
    except Exception as exc:
        messagebox.showerror("Erro", str(exc))
        return

    btn.config(state="disabled", text="Executando...")
    status.config(text="Processando...")
    root.update()

    def executar_async() -> None:
        setup_logging(settings.logs_dir)

        async def tarefa() -> None:
            runner = AutomationRunner(settings, credentials)
            result = await runner.run()
            report = ReportGenerator(settings.output_dir)
            md_path, _json_path = report.generate(result)
            logger.info("Relatorio gerado: %s", md_path)

            root.after(
                0,
                lambda: status.config(
                    text=f"Concluido! {result.total_os} OS processadas"
                ),
            )
            root.after(
                0,
                lambda: messagebox.showinfo(
                    "Sucesso",
                    f"Processamento finalizado!\n"
                    f"{result.total_os} OS processadas "
                    f"({result.success_count} sucesso, "
                    f"{result.failure_count} falhas).",
                ),
            )

        try:
            asyncio.run(tarefa())
        except Exception as exc:
            logger.error("Erro na execucao: %s", exc, exc_info=True)
            root.after(0, lambda: status.config(text="Erro! Veja o log"))
            root.after(0, lambda: messagebox.showerror("Erro", str(exc)))
        finally:
            root.after(0, lambda: btn.config(state="normal", text="Iniciar"))

    threading.Thread(target=executar_async, daemon=True).start()


def abrir_env() -> None:
    """Abre o .env no bloco de notas, criando um template se nao existir."""
    env_path = _base_dir() / ".env"
    if not env_path.exists():
        env_path.write_text(
            "OMIE_EMAIL=\n"
            "OMIE_SENHA=\n"
            "OMIE_EMPRESA=PFO Turismo\n"
            "OMIE_URL=https://app.omie.com.br/\n"
            "OMIE_RETRIES_MAX=3\n"
            "OMIE_RETRY_DELAY_S=2\n"
            "OMIE_TIMEOUT_MS=30000\n"
            "OMIE_HEADLESS=false\n",
            encoding="utf-8",
        )
    subprocess.Popen(["notepad.exe", str(env_path)])


# --- Interface ---
root = tk.Tk()
root.title("Automação NFS-e - Omie")
root.geometry("400x260")
root.resizable(False, False)

tk.Label(
    root, text="Faturamento de Ordens de Serviço", font=("Arial", 12, "bold")
).pack(pady=(14, 4))

tk.Label(
    root, text="Omie - NFS-e (Kanban)", font=("Arial", 9), foreground="gray"
).pack()

frame = ttk.Frame(root, padding=10)
frame.pack()

tk.Label(
    frame,
    text="Fatura automaticamente todas as OS da coluna "
    "'Ordem de Serviço' para 'Faturado'.",
    wraplength=340,
    justify="center",
    foreground="gray",
).pack(pady=(0, 8))

btn = ttk.Button(root, text="Iniciar", command=rodar)
btn.pack(pady=(6, 2))

ttk.Button(root, text="Configurar .env", command=abrir_env).pack(pady=2)

status = ttk.Label(root, text="Pronto", foreground="gray")
status.pack(pady=(8, 0))

_logs = _base_dir() / "logs"
ttk.Label(root, text=str(_logs), foreground="gray", font=("Arial", 7)).pack(pady=(2, 0))

if __name__ == "__main__":
    root.mainloop()

"""Janelas de dialogo auxiliares (Tkinter).

Usadas quando a automacao precisa de interacao humana, ex.: codigo da
autenticacao em dois fatores. A janela roda em thread separada para nao
bloquear o event loop do Playwright.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from omie.services.logger import get_logger

logger = get_logger(__name__)


def ask_2fa_code(
    message: str = "Digite o código de verificação enviado para continuar:",
) -> str | None:
    """Abre uma janela solicitando o codigo 2FA e retorna o valor digitado.

    Returns:
        Codigo informado pelo usuario, ou ``None`` se cancelado/fechado.
    """
    resultado: dict[str, str | None] = {"code": None}

    def _dialog() -> None:
        root = tk.Tk()
        root.title("Autenticação em dois fatores")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="Autenticação em dois fatores",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(0, 6))

        ttk.Label(
            frame, text=message, wraplength=340, justify="left",
        ).pack(pady=(0, 10))

        entry = ttk.Entry(
            frame, width=20, font=("Consolas", 14), justify="center",
        )
        entry.pack(pady=(0, 12))
        entry.focus_set()

        def confirmar(_event: object | None = None) -> None:
            resultado["code"] = entry.get().strip()
            root.destroy()

        def cancelar() -> None:
            resultado["code"] = None
            root.destroy()

        botoes = ttk.Frame(frame)
        botoes.pack()
        ttk.Button(botoes, text="OK", command=confirmar).pack(side="left", padx=4)
        ttk.Button(botoes, text="Cancelar", command=cancelar).pack(side="left", padx=4)

        entry.bind("<Return>", confirmar)
        root.protocol("WM_DELETE_WINDOW", cancelar)

        # Centraliza a janela.
        root.update_idletasks()
        largura = root.winfo_width()
        altura = root.winfo_height()
        x = max(0, (root.winfo_screenwidth() - largura) // 2)
        y = max(0, (root.winfo_screenheight() - altura) // 2)
        root.geometry(f"+{x}+{y}")

        root.mainloop()

    thread = threading.Thread(target=_dialog, daemon=True)
    thread.start()
    thread.join()

    if resultado["code"]:
        logger.info("Codigo 2FA informado pelo usuario.")
    else:
        logger.warning("Codigo 2FA nao informado (janela cancelada).")
    return resultado["code"]

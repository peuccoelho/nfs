"""Janelas de dialogo auxiliares (Tkinter).

Usadas quando a automacao precisa de interacao humana, ex.: codigo da
autenticacao em dois fatores ou selecao da empresa a processar. As janelas
rodam em thread separada para nao bloquear o event loop do Playwright, caso exista.
"""
from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Sequence
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


def ask_empresa(opcoes: Sequence[str]) -> str | None:
    """Abre uma janela para escolher qual empresa faturar.

    Args:
        opcoes: nomes das empresas disponiveis (ex.: 'PFO Turismo', 'Nucleo').

    Returns:
        Nome da empresa escolhida, ou ``None`` se a janela foi cancelada.
    """
    resultado: dict[str, str | None] = {"empresa": None}

    def _dialog() -> None:
        root = tk.Tk()
        root.title("Selecionar empresa")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Qual empresa deve ser processada?",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(0, 6))

        ttk.Label(
            frame,
            text="Selecione a empresa em que as Ordens de Serviço serão faturas:",
            wraplength=360,
            justify="left",
        ).pack(pady=(0, 10))

        var = tk.StringVar(value=opcoes[0] if opcoes else "")
        for nome in opcoes:
            ttk.Radiobutton(frame, text=nome, variable=var, value=nome).pack(
                anchor="w", pady=2
            )

        def confirmar(_event: object | None = None) -> None:
            resultado["empresa"] = var.get()
            root.destroy()

        def cancelar() -> None:
            resultado["empresa"] = None
            root.destroy()

        botoes = ttk.Frame(frame)
        botoes.pack(pady=(12, 0))
        ttk.Button(botoes, text="OK", command=confirmar).pack(side="left", padx=4)
        ttk.Button(botoes, text="Cancelar", command=cancelar).pack(side="left", padx=4)

        root.bind("<Return>", confirmar)
        root.protocol("WM_DELETE_WINDOW", cancelar)

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

    if resultado["empresa"]:
        logger.info("Empresa escolhida pelo usuario: '%s'.", resultado["empresa"])
    else:
        logger.warning("Nenhuma empresa escolhida (janela cancelada).")
    return resultado["empresa"]

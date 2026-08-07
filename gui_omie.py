#! /usr/bin/env python3
"""Interface grafica da automacao de faturamento de OS no Omie.

Permite escolher a empresa, o modo (simulacao/faturamento real) e acompanhar o
progresso ao vivo. A execucao roda em thread separada; janelas de 2FA e de
selecao de empresa sao abertas automaticamente pela automacao quando preciso.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from omie.automation.runner import AutomationRunner
from omie.config import Credentials, Settings
from omie.config.settings import SUPPORTED_EMPRESAS
from omie.services.logger import get_logger, setup_logging
from omie.services.report import ExecutionResult, ReportGenerator

logger = get_logger(__name__)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


class OmeGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._empresa = tk.StringVar(value=SUPPORTED_EMPRESAS[0])
        self._modo = tk.StringVar(value="real")  # "real" | "simulacao"
        self._executar = False

        self._build()

    def _build(self) -> None:
        root = self.root
        root.title("Automação NFS-e - Omie")
        root.geometry("460x470")
        root.minsize(440, 440)

        tk.Label(
            root, text="Faturamento de Ordens de Serviço", font=("Arial", 13, "bold")
        ).pack(pady=(14, 2))
        tk.Label(
            root, text="Omie - NFS-e", font=("Arial", 9), foreground="gray"
        ).pack()

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        # Empresa
        ttk.Label(frame, text="Empresa:", font=("Arial", 10, "bold")).pack(anchor="w")
        for emp in SUPPORTED_EMPRESAS:
            ttk.Radiobutton(
                frame, text=emp, variable=self._empresa, value=emp
            ).pack(anchor="w", padx=14)

        # Modo
        ttk.Label(frame, text="Modo:", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(8, 0)
        )
        ttk.Radiobutton(
            frame,
            text="Faturamento real (emite a NFS-e)",
            variable=self._modo,
            value="real",
        ).pack(anchor="w", padx=14)
        ttk.Radiobutton(
            frame,
            text="Simulação (apenas inspeção, não fatura)",
            variable=self._modo,
            value="simulacao",
        ).pack(anchor="w", padx=14)

        # Acoes
        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", pady=(14, 4))
        self._btn_iniciar = ttk.Button(
            botoes, text="Iniciar", command=self._rodar
        )
        self._btn_iniciar.pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(botoes, text="Config .env", command=self._open_env).pack(
            side="left", expand=True, fill="x", padx=(4, 0)
        )

        botoes2 = ttk.Frame(frame)
        botoes2.pack(fill="x", pady=(0, 4))
        ttk.Button(botoes2, text="Abrir logs", command=self._open_logs).pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        ttk.Button(
            botoes2, text="Abrir relatórios", command=self._open_output
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Status / progresso
        self._status = ttk.Label(root, text="Pronto", foreground="#0b7285")
        self._status.pack(padx=12, pady=(0, 4))

        self._progress = ttk.Progressbar(root, mode="indeterminate")
        self._progress.pack(fill="x", padx=12, pady=(0, 4))

        # Log ao vivo
        ttk.Label(frame, text="Progresso:", font=("Arial", 9, "bold")).pack(
            anchor="w", pady=(8, 2)
        )
        self._log = tk.Text(
            frame,
            height=9,
            state="disabled",
            bg="#0e1116",
            fg="#e6edf3",
            font=("Consolas", 9),
            wrap="word",
        )
        self._log.pack(fill="both", expand=True)

        _logs = _base_dir() / "logs"
        ttk.Label(
            root, text=str(_logs), foreground="gray", font=("Arial", 7)
        ).pack(pady=(2, 4))

    # --- Helpers de UI ---
    def _write(self, texto: str) -> None:
        def apply() -> None:
            self._log.config(state="normal")
            self._log.insert("end", texto + "\n")
            self._log.see("end")
            self._log.config(state="disabled")

        self.root.after(0, apply)

    def _set_status(self, texto: str) -> None:
        self.root.after(0, lambda: self._status.config(text=texto))

    def _set_running(self, ligado: bool) -> None:
        self._executar = ligado

        def apply() -> None:
            if ligado:
                self._btn_iniciar.config(state="disabled", text="Executando...")
                self._progress.start(12)
            else:
                self._btn_iniciar.config(state="normal", text="Iniciar")
                self._progress.stop()

        self.root.after(0, apply)

    def _open_env(self) -> None:
        env_path = _base_dir() / ".env"
        if not env_path.exists():
            env_path.write_text(
                "OMIE_EMAIL=\n"
                "OMIE_SENHA=\n"
                "OMIE_EMPRESA=" + self._empresa.get() + "\n"
                "OMIE_URL=https://app.omie.com.br/\n"
                "OMIE_RETRIES_MAX=3\n"
                "OMIE_RETRY_DELAY_S=2\n"
                "OMIE_TIMEOUT_MS=30000\n"
                "OMIE_HEADLESS=false\n",
                encoding="utf-8",
            )
        subprocess.Popen(["notepad.exe", str(env_path)])

    def _abrir(self, caminho: Path) -> None:
        caminho.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["explorer.exe", str(caminho)])
        except Exception:  # pragma: no cover
            messagebox.showerror("Erro", f"Nao foi possivel abrir: {caminho}")

    def _open_logs(self) -> None:
        self._abrir(_base_dir() / "logs")

    def _open_output(self) -> None:
        self._abrir(_base_dir() / "output")

    # --- Execucao ---
    def _rodar(self) -> None:
        if self._executar:
            return
        try:
            self._settings = Settings.load()
            self._credentials = Credentials.load()
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return

        self._rodar_autorizado()

    def _rodar_autorizado(self) -> None:
        self._set_running(True)
        self._set_status("Iniciando...")

        def executar_async() -> None:
            setup_logging(self._settings.logs_dir)
            start = datetime.now()

            async def tarefa() -> None:
                runner = AutomationRunner(
                    self._settings,
                    self._credentials,
                    dry_run=self._modo.get() == "simulacao",
                    empresa=self._empresa.get(),
                )
                result = await runner.run()
                self._finalizar(result, start)

            try:
                asyncio.run(tarefa())
            except Exception as exc:
                logger.error("Erro na execucao: %s", exc, exc_info=True)
                self._write(f"[erro] {exc}")
                self._set_status("Erro! Veja o log")
                messagebox.showerror("Erro", str(exc))
            finally:
                self._set_running(False)

        threading.Thread(target=executar_async, daemon=True).start()

    def _finalizar(self, result: ExecutionResult, start: datetime) -> None:
        report = ReportGenerator(self._settings.output_dir)
        try:
            md_path, _json_path = report.generate(result)
            self._write(f"[relatorio] {md_path.name}")
        except Exception as exc:
            logger.error("Falha ao gerar relatorio: %s", exc)

        resumo = (
            f"Concluído em {self._settings.output_dir}\n"
            f"{result.total_os} OS processadas "
            f"({result.success_count} sucesso, "
            f"{result.pulada_count} puladas, "
            f"{result.failure_count} falhas) em {result.total_seconds:.0f}s."
        )
        self._set_status(
            f"Concluído! {result.total_os} OS processadas"
            f" ({result.success_count} sucesso, "
            f"{result.failure_count} falhas)."
        )
        messagebox.showinfo("Concluído", resumo)


def main() -> None:
    root = tk.Tk()
    OmeGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
"""Configuracoes da aplicacao carregadas do ambiente (.env).

Centraliza caminhos, timeouts e parametros de comportamento. Os valores podem
ser sobrescritos via variaveis OMIE_* no arquivo .env.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Empresas disponiveis para selecao no portal de apps (apos o login).
SUPPORTED_EMPRESAS: tuple[str, ...] = ("PFO Turismo", "Nucleo")


def project_root() -> Path:
    """Retorna a raiz do projeto (pasta do .exe quando empacotado)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Configuracoes imutaveis da automacao."""

    url_login: str
    url_app: str
    empresa: str
    timeout_ms: int
    result_wait_ms: int
    retries_max: int
    retry_delay_s: float
    headless: bool
    base: Path
    logs_dir: Path
    output_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        base = project_root()
        load_dotenv(dotenv_path=base / ".env")

        return cls(
            url_login=os.getenv("OMIE_URL", "https://app.omie.com.br/"),
            url_app=os.getenv(
                "OMIE_APP_URL", "https://app.omie.com.br/gestao/pfo-cow05sxa/"
            ),
            empresa=os.getenv("OMIE_EMPRESA", "PFO Turismo"),
            timeout_ms=int(os.getenv("OMIE_TIMEOUT_MS", "30000")),
            result_wait_ms=int(os.getenv("OMIE_RESULT_WAIT_MS", "15000")),
            retries_max=int(os.getenv("OMIE_RETRIES_MAX", "3")),
            retry_delay_s=float(os.getenv("OMIE_RETRY_DELAY_S", "2.0")),
            headless=os.getenv("OMIE_HEADLESS", "false").lower() == "true",
            base=base,
            logs_dir=base / "logs",
            output_dir=base / "output",
        )

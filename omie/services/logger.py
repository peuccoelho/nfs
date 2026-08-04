"""Logging estruturado da automacao (console + arquivo)."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(logs_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configura o logging raiz com saida em console e arquivo.

    O arquivo de log fica em ``logs_dir`` com nome datahora no padrao
    ``omie_automation_YYYYMMDD_HHMMSS.log``.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)
    if root.hasHandlers():
        root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    arquivo = logs_dir / f"omie_automation_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(arquivo, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root.info("Logging inicializado. Arquivo: %s", arquivo)
    return root


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado."""
    return logging.getLogger(name)

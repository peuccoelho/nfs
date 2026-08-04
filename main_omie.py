#! /usr/bin/env python3
"""Ponto de entrada (CLI) da automacao de faturamento de OS no Omie.

Uso:
    python main_omie.py
"""
from __future__ import annotations

import asyncio
import sys

from omie.automation.runner import AutomationRunner
from omie.config import Credentials, Settings
from omie.services.logger import get_logger, setup_logging
from omie.services.report import ReportGenerator


async def main() -> int:
    settings = Settings.load()
    setup_logging(settings.logs_dir)
    logger = get_logger(__name__)

    try:
        credentials = Credentials.load()
    except Exception as exc:
        logger.error("Configuracao invalida: %s", exc)
        return 1

    logger.info("Iniciando automacao Omie (empresa '%s')...", settings.empresa)
    try:
        runner = AutomationRunner(settings, credentials)
        result = await runner.run()
        report = ReportGenerator(settings.output_dir)
        md_path, _json_path = report.generate(result)
        logger.info("Relatorio gerado: %s", md_path)
        return 0
    except Exception as exc:
        logger.error("Execucao encerrada: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

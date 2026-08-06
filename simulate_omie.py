#! /usr/bin/env python3
"""Simulacao guiada do fluxo Omie com Playwright (modo inspecao).

Percorre as mesmas etapas da automacao real (login, empresa, NFS-e, kanban e
SEFAZ) registrando screenshots, HTML, trace e um relatorio de seletores para
analisar e corrigir os modulos de ``selectors``.

Uso:
    python simulate_omie.py                  # dry-run: inspeciona sem faturar
    python simulate_omie.py --full           # executa o faturamento real
    python simulate_omie.py --no-trace       # sem trace (apenas screenshots)

Saida: logs/simulacao/<timestamp>/
    - trace.zip          abrir com: python -m playwright show-trace trace.zip
    - fluxo.md           log das etapas (URL, titulo, timestamps)
    - seletores.md/.json relatorio de elementos reais e validacao dos seletores
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omie.automation.runner import AutomationRunner
from omie.config import Credentials, Settings
from omie.config.settings import SUPPORTED_EMPRESAS
from omie.services.logger import get_logger, setup_logging
from omie.simulation.recorder import SimulationRecorder


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simula o fluxo Omie e registra telas/seletores via Playwright."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Executa o faturamento real (arrasta as OS para 'Faturado'). "
        "Por padrao roda em dry-run (sem alterar dados).",
    )
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Nao grava o trace do Playwright (apenas screenshots/HTML).",
    )
    parser.add_argument(
        "--empresa",
        choices=SUPPORTED_EMPRESAS,
        help="Empresa para faturar as OS (ex.: Nucleo). Se omitida, o script "
        "perguntara ao final do login.",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    settings = Settings.load()
    setup_logging(settings.logs_dir)
    logger = get_logger(__name__)

    try:
        credentials = Credentials.load()
    except Exception as exc:
        logger.error("Configuracao invalida: %s", exc)
        return 1

    base_dir = settings.base / "logs" / "simulacao"
    recorder = SimulationRecorder(settings, base_dir)
    trace_path: Path | None = None
    if not args.no_trace:
        trace_path = recorder.root / "trace.zip"

    modo = "FULL (faturamento real)" if args.full else "DRY-RUN (sem alterar dados)"
    logger.info(
        "Iniciando simulacao do fluxo Omie em modo %s (empresa '%s')...",
        modo,
        settings.empresa,
    )

    runner = AutomationRunner(
        settings,
        credentials,
        recorder=recorder,
        dry_run=not args.full,
        trace_path=trace_path,
        session_path=settings.base / "logs" / "sessao_omie.json",
        empresa=args.empresa,
    )

    try:
        await runner.run()
        logger.info("Simulacao concluida com sucesso.")
    except Exception as exc:
        logger.error("Simulacao interrompida: %s", exc, exc_info=True)
    finally:
        raiz = recorder.finish()

    logger.info("=" * 60)
    logger.info("Artefatos da simulacao em: %s", raiz)
    logger.info("  - %s", raiz / "fluxo.md")
    logger.info("  - %s", raiz / "seletores.md")
    logger.info("  - %s", raiz / "seletores.json")
    if trace_path is not None and trace_path.exists():
        logger.info(
            "  - %s\n    Para abrir: python -m playwright show-trace %s",
            trace_path,
            trace_path,
        )
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))

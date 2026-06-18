#! /usr/bin/env python3
"""Automatizador de exportacao de XMLs de NFS-e do portal da Prefeitura de Camacari.

Uso:
    python main.py --mes 5 --ano 2026
"""

import asyncio
import sys

from config import Config
from portal import PortalNFSE
from utils import setup_logging, get_logger

logger = get_logger(__name__)


async def main() -> None:
    """Ponto de entrada principal da aplicacao."""
    setup_logging()

    try:
        # Carrega configuracoes (CLI + .env)
        config = Config.parse_cli()
        logger.info("Iniciando exportacao NFS-e - Mes %d/%d", config.mes, config.ano)

        # Cria a instancia do portal
        portal = PortalNFSE(config)

        # Executa o fluxo completo
        await portal.iniciar()
        await portal.navegar_para_nota_fiscal()
        await portal.executar_consulta()

        logger.info("Exportacao concluida com sucesso!")

    except ValueError as e:
        logger.error("Erro de configuracao: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operacao interrompida pelo usuario")
        sys.exit(0)
    except Exception as e:
        logger.error("Erro inesperado: %s", e)
        sys.exit(2)
    finally:
        # Garante que o navegador seja fechado
        if "portal" in locals():
            await portal.fechar()


if __name__ == "__main__":
    asyncio.run(main())

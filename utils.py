import calendar
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging() -> None:
    """Configura o logging padrao da aplicacao."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado."""
    return logging.getLogger(name)


def split_date_range(ano: int, mes: int) -> list[tuple[str, str]]:
    """Divide um mes em 2 periodos: 1-15 e 16-ultimo_dia.

    Args:
        ano: Ano da consulta.
        mes: Mes da consulta (1-12).

    Returns:
        Lista de tuplas (data_inicial, data_final) no formato DD/MM/AAAA.
    """
    _, ultimo_dia = calendar.monthrange(ano, mes)

    return [
        (f"01/{mes:02d}/{ano}", f"15/{mes:02d}/{ano}"),
        (f"16/{mes:02d}/{ano}", f"{ultimo_dia:02d}/{mes:02d}/{ano}"),
    ]


def _base_dir() -> Path:
    """Retorna o diretorio base (pai do .exe ou do script)."""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def criar_diretorio_downloads(ano: int, mes: int) -> Path:
    """Cria e retorna o caminho do diretorio de downloads para o mes/ano.

    Exemplo: downloads/2026-05/
    """
    diretorio: Path = _base_dir() / "downloads" / f"{ano}-{mes:02d}"
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio


def xml_ja_existe(diretorio: Path, numero_nf: str) -> bool:
    """Verifica se o XML de uma determinada NF ja foi baixado."""
    return (diretorio / f"NF_{numero_nf}.xml").exists()


def extrair_numero_nf(nome_zip: str) -> str:
    """Tenta extrair o numero da NF a partir do nome do arquivo ZIP."""
    return nome_zip.replace(".zip", "").strip()

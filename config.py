import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """Central configuration loaded from .env and CLI arguments."""

    def __init__(self) -> None:
        # Carrega variaveis do arquivo .env
        env_path: Path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Credenciais do portal
        self.usuario: str = os.getenv("USUARIO", "")
        self.senha: str = os.getenv("SENHA", "")

        # Valores padrao via CLI
        self.mes: int = 0
        self.ano: int = 0

    @staticmethod
    def parse_cli() -> "Config":
        """Interpreta argumentos da linha de comando e retorna um objeto Config."""
        parser = argparse.ArgumentParser(
            description="Automatizador de exportacao de XMLs de NFS-e - Prefeitura de Camacari"
        )
        parser.add_argument(
            "--mes",
            type=int,
            required=True,
            help="Mes para consulta (1-12)",
        )
        parser.add_argument(
            "--ano",
            type=int,
            required=True,
            help="Ano para consulta (ex: 2026)",
        )
        args = parser.parse_args()

        cfg = Config()
        cfg.mes = args.mes
        cfg.ano = args.ano

        if not cfg.usuario or not cfg.senha:
            raise ValueError(
                "Credenciais nao encontradas. "
                "Certifique-se de que o arquivo .env existe com USUARIO e SENHA."
            )

        return cfg

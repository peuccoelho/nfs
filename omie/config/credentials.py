"""Credenciais de acesso ao portal Omie (carregadas do .env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from omie.config.settings import project_root
from omie.utils.exceptions import CredentialsError


@dataclass(frozen=True)
class Credentials:
    """E-mail e senha usados no login do portal Omie."""

    email: str
    senha: str

    @classmethod
    def load(cls) -> "Credentials":
        base = project_root()
        load_dotenv(dotenv_path=base / ".env")

        email = os.getenv("OMIE_EMAIL", "")
        senha = os.getenv("OMIE_SENHA", "")

        if not email or not senha:
            raise CredentialsError(
                "Credenciais OMIE_EMAIL/OMIE_SENHA nao encontradas no arquivo .env"
            )

        return cls(email=email, senha=senha)

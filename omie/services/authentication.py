"""Servico de autenticacao (2FA) do portal Omie."""
from __future__ import annotations

import asyncio

from playwright.async_api import Page

from omie.automation import dialogs
from omie.automation.selectors import login as login_selectors
from omie.services.logger import get_logger
from omie.utils.exceptions import TwoFactorError

logger = get_logger(__name__)


class AuthenticationService:
    """Lida com desafios de autenticacao em dois fatores."""

    async def handle_two_factor(self, page: Page) -> None:
        """Pausa a automacao, pede o codigo ao usuario e o submete."""
        logger.info("Autenticacao em dois fatores detectada.")

        code = await asyncio.to_thread(dialogs.ask_2fa_code)
        if not code:
            raise TwoFactorError("Codigo 2FA nao informado pelo usuario")

        campo = login_selectors.two_factor_input(page)
        await campo.fill(code)
        await login_selectors.two_factor_submit(page).click()
        logger.info("Codigo 2FA enviado.")

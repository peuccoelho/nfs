"""Etapa de login no portal Omie (com suporte a autenticacao 2FA)."""
from __future__ import annotations

from playwright.async_api import Page, TimeoutError

from omie.automation.selectors import login as login_selectors
from omie.automation.waits import Waits
from omie.config.credentials import Credentials
from omie.config.settings import Settings
from omie.services.authentication import AuthenticationService
from omie.services.logger import get_logger
from omie.utils.exceptions import LoginError

logger = get_logger(__name__)


class LoginFlow:
    """Realiza o login no portal Omie."""

    def __init__(
        self,
        page: Page,
        settings: Settings,
        credentials: Credentials,
        authentication: AuthenticationService,
        waits: Waits,
    ) -> None:
        self._page = page
        self._settings = settings
        self._credentials = credentials
        self._authentication = authentication
        self._waits = waits

    async def execute(self) -> None:
        """Abre a pagina de login, autentica e aguarda a home do Omie."""
        logger.info("Acessando o portal Omie (%s)...", self._settings.url_login)
        await self._page.goto(self._settings.url_login, wait_until="domcontentloaded")
        await self._waits.visible(
            login_selectors.email_input(self._page),
            timeout=20000,
            description="campo de e-mail",
        )

        await self._fill_credentials()
        await self._submit()
        if await self._needs_two_factor():
            await self._authentication.handle_two_factor(self._page)

        await self._wait_logged_in()
        logger.info("Login concluido.")

    async def _fill_credentials(self) -> None:
        """Preenche e-mail e senha (fluxo em 1 ou 2 etapas)."""
        await login_selectors.email_input(self._page).fill(self._credentials.email)

        senha = login_selectors.password_input(self._page)
        try:
            await senha.wait_for(state="visible", timeout=2000)
        except TimeoutError:
            logger.info("Login em duas etapas: avancando para a tela de senha...")
            await login_selectors.continue_button(self._page).click()
            await self._waits.visible(
                senha, timeout=15000, description="campo de senha"
            )
        await senha.fill(self._credentials.senha)

    async def _submit(self) -> None:
        await login_selectors.submit_button(self._page).click()
        await self._waits.for_timeout(1000)

    async def _needs_two_factor(self) -> bool:
        """Verifica se o Omie solicitou o codigo de verificacao."""
        try:
            await self._page.wait_for_function(
                "() => !!(document.querySelector(arg[0]) || document.querySelector(arg[1]))",
                arg=[
                    login_selectors.TWO_FACTOR_INPUT_SELECTOR,
                    login_selectors.APP_HOME_SELECTOR,
                ],
                timeout=12000,
            )
        except TimeoutError:
            logger.warning("Nao foi possivel confirmar a tela apos o login.")
            return False
        return await login_selectors.two_factor_input(self._page).is_visible(
            timeout=1500
        )

    async def _wait_logged_in(self) -> None:
        """Aguarda a home do Omie (ou confirma via URL)."""
        try:
            await login_selectors.app_home_marker(self._page).wait_for(
                state="visible", timeout=30000
            )
        except TimeoutError:
            url = self._page.url
            if "login" in url.lower():
                raise LoginError("Login no Omie nao confirmado")
            logger.info("Sessao iniciada (URL atual: %s).", url)

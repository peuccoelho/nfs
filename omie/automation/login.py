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
        await self._goto_with_retry()

        if await self._try_skip_if_logged_in():
            logger.info("Sessao ja ativa (persistida); pulando login.")
        else:
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

    async def _goto_with_retry(self) -> None:
        """Navega ate o portal com retries (rede instavel/internet oscilante)."""
        for tentativa in range(1, 4):
            try:
                await self._page.goto(
                    self._settings.url_login, wait_until="domcontentloaded"
                )
                return
            except Exception as exc:
                logger.warning(
                    "Falha ao abrir o portal (tentativa %d/3): %s",
                    tentativa,
                    exc,
                )
                if tentativa < 3:
                    await self._page.wait_for_timeout(2000 * tentativa)
        raise LoginError("Nao foi possivel abrir o portal Omie")

    async def _try_skip_if_logged_in(self) -> bool:
        """Retorna ``True`` se o email nao aparecer (sessao ja ativa).

        Com rede lenta o formulario pode demorar a renderizar; aguardamos ate o
        campo de e-mail OU o portal de apps/URL de sessao aparecerem. Se em ate
        15s nada indicar que estamos na tela de login, assumimos sessao ativa.
        """
        campo = login_selectors.email_input(self._page)
        for _ in range(30):
            try:
                if await campo.count() and await campo.first.is_visible(
                    timeout=1000
                ):
                    return False
            except Exception:
                pass
            try:
                if await self._is_apps_portal_url():
                    return True
            except Exception:
                pass
            await self._page.wait_for_timeout(500)
        logger.info("Login nao detectado em 15s; assumindo sessao ja ativa.")
        return True

    async def _fill_credentials(self) -> None:
        """Preenche e-mail e senha (fluxo real: e-mail -> Continuar -> senha)."""
        email = login_selectors.email_textbox(self._page)
        try:
            await email.wait_for(state="visible", timeout=3000)
        except TimeoutError:
            email = login_selectors.email_input(self._page)
        await email.fill(self._credentials.email)

        senha = login_selectors.password_textbox(self._page)
        try:
            await senha.wait_for(state="visible", timeout=2500)
        except TimeoutError:
            senha = login_selectors.password_input(self._page)
            logger.info("Avancando para a tela de senha (botao 'Continuar')...")
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
        campo = login_selectors.two_factor_input(self._page)
        for _ in range(24):
            try:
                if await campo.count() and await campo.first.is_visible(
                    timeout=1000
                ):
                    return True
            except Exception:
                pass
            await self._page.wait_for_timeout(500)
        logger.warning("Tela de 2FA nao confirmada apos o login.")
        return False

    async def _wait_logged_in(self) -> None:
        """Aguarda a home do Omie (ou confirma via URL)."""
        # O portal de apps (selecao de empresa) ja indica login concluido.
        if await self._is_apps_portal_url():
            logger.info("Sessao iniciada (portal de apps).")
            return
        try:
            await login_selectors.app_home_marker(self._page).wait_for(
                state="visible", timeout=30000
            )
        except TimeoutError:
            url = self._page.url
            if "login" in url.lower():
                raise LoginError("Login no Omie nao confirmado")
            logger.info("Sessao iniciada (URL atual: %s).", url)

    async def _is_apps_portal_url(self) -> bool:
        """True quando a pagina esta no portal de apps (selecao de empresa)."""
        try:
            await self._page.wait_for_url(
                "**/meus-aplicativos**", timeout=5000
            )
            return True
        except TimeoutError:
            return False

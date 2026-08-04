"""Etapas de navegacao: selecao de empresa e acesso ao modulo NFS-e."""
from __future__ import annotations

from playwright.async_api import Page, TimeoutError

from omie.automation.selectors import kanban as kanban_selectors
from omie.automation.selectors import navigation as nav_selectors
from omie.automation.waits import Waits
from omie.config.settings import Settings
from omie.services.logger import get_logger

logger = get_logger(__name__)


class Navigation:
    """Navega pelo portal Omie ate o kanban de ordens de servico."""

    def __init__(self, page: Page, settings: Settings, waits: Waits) -> None:
        self._page = page
        self._settings = settings
        self._waits = waits

    async def select_company(self) -> None:
        """Localiza a empresa configurada e clica em 'Acessar'."""
        logger.info("Selecionando empresa '%s'...", self._settings.empresa)
        card = nav_selectors.company_card(self._page, self._settings.empresa)
        await self._waits.visible(
            card, timeout=30000, description=f"empresa '{self._settings.empresa}'"
        )
        await nav_selectors.access_button_for_company(
            self._page, self._settings.empresa
        ).click()
        await self._waits.for_timeout(2000)
        logger.info("Empresa '%s' selecionada.", self._settings.empresa)

    async def go_to_os_kanban(self) -> None:
        """Navega em Servicos > NFS-e e exibe as etapas das OS."""
        logger.info("Navegando para Servicos > NFS-e...")
        await self._click_menu(nav_selectors.MENU_SERVICOS)
        await self._click_menu(nav_selectors.MENU_NFSE)
        await self._waits.for_timeout(3000)

        toggle = nav_selectors.kanban_toggle(self._page)
        try:
            await toggle.first.wait_for(state="visible", timeout=8000)
            await toggle.first.click()
            logger.info("Exibindo etapas das ordens de servico.")
        except TimeoutError:
            logger.info("Opcao de etapas nao encontrada; usando a visao padrao.")

        await self._waits.visible(
            kanban_selectors.column(
                self._page, kanban_selectors.SOURCE_COLUMN_TITLE
            ),
            timeout=30000,
            description="coluna 'Ordem de Serviço'",
        )
        logger.info("Kanban de ordens de servico aberto.")

    async def _click_menu(self, nome: str) -> None:
        """Clica em um item do menu pelo texto."""
        item = nav_selectors.menu_item(self._page, nome)
        await self._waits.visible(item, timeout=15000, description=f"menu '{nome}'")
        await item.click()
        await self._waits.for_timeout(1500)

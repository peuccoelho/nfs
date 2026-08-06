"""Etapas de navegacao: empresa, onboarding e acesso a lista de OS."""
from __future__ import annotations

from playwright.async_api import Page, TimeoutError

from omie.automation.selectors import navigation as nav_selectors
from omie.automation.waits import Waits
from omie.config.settings import Settings
from omie.services.logger import get_logger

logger = get_logger(__name__)


class Navigation:
    """Navega pelo portal Omie ate a listagem de Ordens de Servico."""

    def __init__(self, page: Page, settings: Settings, waits: Waits) -> None:
        self._page = page
        self._settings = settings
        self._waits = waits

    async def select_company(self) -> None:
        """Localiza a empresa configurada e clica em 'Acessar'."""
        logger.info("Selecionando empresa '%s'...", self._settings.empresa)
        card = nav_selectors.company_card(self._page, self._settings.empresa)
        await self._waits.visible(
            card, timeout=45000, description=f"empresa '{self._settings.empresa}'"
        )
        await self._waits.settle(quiet_ms=800, max_wait_ms=10000, description="portal")
        await self._waits.click(
            nav_selectors.access_button_for_company(
                self._page, self._settings.empresa
            ),
            timeout=20000,
            description=f"acessar empresa '{self._settings.empresa}'",
        )
        await self._waits.for_timeout(2000)
        logger.info("Empresa '%s' selecionada.", self._settings.empresa)

    async def go_to_os_list(self) -> None:
        """Abre Servicos > NFS-e > Listar todas as ordens de servico.

        Fecha o onboarding ('Depois') se estiver presente e aguarda a listagem
        de OS.
        """
        await self.dismiss_onboarding(wait_attach=3000)
        logger.info("Navegando para '%s'...", nav_selectors.MENU_SERVICOS)
        await self._waits.visible(
            nav_selectors.servicos_menu_link(self._page),
            timeout=60000,
            description="menu 'Servicos e NFS-e'",
        )
        await self._waits.settle(quiet_ms=800, max_wait_ms=15000, description="menu")
        await self._waits.click(
            nav_selectors.servicos_menu_link(self._page),
            timeout=20000,
            description="menu 'Servicos e NFS-e'",
        )
        await self._waits.for_timeout(2000)

        # O popup 'Primeiros Passos' da conta Nucleo abre apos entrar no modulo
        # (Codegen: menu -> 'Depois' -> 'Fechar'); fechamo-lo agora, antes de
        # acessar a listagem, para nao interceptar o clique abaixo.
        await self.dismiss_onboarding(wait_attach=4000)
        await self.dismiss_primeiros_passos()

        logger.info(
            "Abrindo a listagem de OS ('%s')...", nav_selectors.OS_LIST_LINK
        )
        await self._waits.visible(
            nav_selectors.os_list_link(self._page),
            timeout=45000,
            description="link 'Listar todas as'",
        )
        await self._waits.click(
            nav_selectors.os_list_link(self._page),
            timeout=20000,
            description="link 'Listar todas as'",
        )
        await self._waits.settle(quiet_ms=1000, max_wait_ms=20000, description="lista")

        try:
            await self._waits.visible(
                nav_selectors.os_list_link(self._page),
                timeout=20000,
                description="listagem de OS",
            )
        except TimeoutError:
            logger.info("Nao foi possivel confirmar a listagem; prosseguindo.")
        logger.info("Listagem de Ordens de Servico aberta.")

    async def dismiss_onboarding(self, wait_attach: int = 15000) -> None:
        """Clica em 'Depois' caso o tour/onboarding esteja aberto.

        Deve ser chamado logo apos o app abrir (em nova aba), antes de qualquer
        navegacao, para o tour nao interceptar os cliques. Aguarda o popup
        aparecer (pode abrir com alguns segundos de atraso).
        """
        botao = nav_selectors.onboarding_later_button(self._page)
        try:
            await botao.first.wait_for(state="attached", timeout=wait_attach)
            if await botao.first.is_visible(timeout=8000):
                await botao.first.click(timeout=10000)
                await self._waits.for_timeout(1500)
                logger.info("Onboarding fechado (botao 'Depois').")
        except Exception as exc:
            logger.debug("Nenhum onboarding presente; seguindo. (%s)", exc)

    async def dismiss_primeiros_passos(self) -> None:
        """Fecha o popup 'Primeiros Passos' (conta Nucleo) via botao 'Fechar'.

        So a conta Nucleo exibe esse popup (guia passo-a-passo do modulo de
        NFS-e); para as demais ele nao aparece e o metodo apenas verifica e
        segue. Confirma o Codegen: botao padrao do sistema 'Fechar'.
        """
        fechar = nav_selectors.primeiros_passos_close_button(self._page)
        try:
            await fechar.wait_for(state="visible", timeout=10000)
        except Exception:
            logger.debug("Nenhum popup 'Primeiros Passos' presente; seguindo.")
            return
        try:
            await fechar.click(timeout=10000)
            await self._waits.for_timeout(1500)
            logger.info("Popup 'Primeiros Passos' fechado (botao 'Fechar').")
        except Exception as exc:
            logger.warning(
                "Nao foi possivel fechar o popup 'Primeiros Passos': %s", exc
            )
            await self._waits.for_timeout(2000)
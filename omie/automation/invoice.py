"""Faturamento de uma ordem de servico (drag & drop no kanban)."""
from __future__ import annotations

from enum import Enum

from playwright.async_api import Locator, Page, TimeoutError

from omie.automation.selectors import kanban as kanban_selectors
from omie.automation.selectors import sefaz as sefaz_selectors
from omie.automation.waits import Waits
from omie.config.settings import Settings
from omie.services.logger import get_logger

logger = get_logger(__name__)

#: JS alternativo que simula eventos de drag HTML5 sobre o elemento sob o ponto.
_DRAG_EVENTS_JS = """(args) => {
  const fromPoint = (x, y) => {
    const el = document.elementFromPoint(x, y);
    if (!el) return null;
    let cur = el;
    while (cur && cur !== document.body && !cur.hasAttribute('draggable')) {
      cur = cur.parentElement;
    }
    return cur && cur !== document.body ? cur : el;
  };
  const src = fromPoint(args.sx, args.sy);
  const dst = fromPoint(args.tx, args.ty);
  if (!src || !dst) return false;
  const dt = new DataTransfer();
  src.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }));
  dst.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: dt }));
  dst.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
  dst.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
  src.dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }));
  return true;
}"""


class BillingOutcome(str, Enum):
    """Resultado de uma tentativa de faturamento."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class InvoiceBiller:
    """Move uma OS da coluna 'Ordem de Servico' para 'Faturado'."""

    def __init__(self, page: Page, settings: Settings, waits: Waits) -> None:
        self._page = page
        self._settings = settings
        self._waits = waits

    async def bill(
        self,
        source_column: Locator,
        target_column: Locator,
        os_id: str,
    ) -> BillingOutcome:
        """Fatura uma OS e retorna o resultado observado.

        Fluxo:
            1. localiza o cartao da OS na coluna de origem;
            2. arrasta para a coluna 'Faturado';
            3. aguarda o resultado: se surgir a mensagem de campos
               obrigatorios, retorna ``ERROR``; caso contrario, considera
               a OS faturada (``SUCCESS``).
        """
        card = await self._find_card(source_column, os_id)
        if card is None:
            logger.warning("OS %s nao encontrada na coluna de origem.", os_id)
            return BillingOutcome.TIMEOUT

        logger.info("Faturando OS %s (arrastando para 'Faturado')...", os_id)
        if not await self._drag(card, target_column, os_id):
            logger.error("Nao foi possivel arrastar a OS %s.", os_id)
            return BillingOutcome.TIMEOUT

        return await self._wait_outcome(os_id)

    async def _find_card(
        self, column: Locator, os_id: str
    ) -> Locator | None:
        """Retorna o cartao da OS dentro da coluna, ou ``None``."""
        cards = kanban_selectors.cards(column)
        count = await cards.count()
        for indice in range(count):
            card = cards.nth(indice)
            texto = await card.text_content()
            if texto and os_id in texto:
                return card
        return None

    async def _drag(self, card: Locator, target: Locator, os_id: str) -> bool:
        """Arrasta o cartao com estrategias em cascata:
        1. drag nativo do Playwright;
        2. movimentacao de mouse;
        3. eventos simulados (fallback).
        """
        try:
            await card.scroll_into_view_if_needed()
            await self._waits.for_timeout(300)
            await card.drag_to(target, timeout=self._settings.timeout_ms)
            return True
        except Exception as exc:
            logger.warning(
                "Drag nativo falhou para OS %s (%s). Tentando mouse...",
                os_id, exc,
            )
            if await self._drag_with_mouse(card, target):
                return True
            logger.warning("Drag com mouse falhou. Tentando eventos simulados...")
            return await self._drag_with_events(card, target)

    async def _drag_with_mouse(self, card: Locator, target: Locator) -> bool:
        """Arrasta simulando a movimentacao fisica do mouse."""
        origem = await card.bounding_box()
        destino = await target.bounding_box()
        if not origem or not destino:
            return False

        sx = origem["x"] + origem["width"] / 2
        sy = origem["y"] + origem["height"] / 2
        tx = destino["x"] + destino["width"] / 2
        ty = destino["y"] + destino["height"] - 20

        await self._page.mouse.move(sx, sy)
        await self._page.mouse.down()
        passos = 12
        for passo in range(1, passos + 1):
            x = sx + (tx - sx) * passo / passos
            y = sy + (ty - sy) * passo / passos
            await self._page.mouse.move(x, y)
            await self._waits.for_timeout(30)
        await self._page.mouse.up()
        await self._waits.for_timeout(500)
        return True

    async def _drag_with_events(self, card: Locator, target: Locator) -> bool:
        """Fallback: despacha eventos de drag HTML5 via JavaScript."""
        origem = await card.bounding_box()
        destino = await target.bounding_box()
        if not origem or not destino:
            return False
        try:
            ok = await self._page.evaluate(
                _DRAG_EVENTS_JS,
                {
                    "sx": origem["x"] + origem["width"] / 2,
                    "sy": origem["y"] + origem["height"] / 2,
                    "tx": destino["x"] + destino["width"] / 2,
                    "ty": destino["y"] + destino["height"] - 20,
                },
            )
            return bool(ok)
        except Exception as exc:
            logger.error("Drag por eventos falhou: %s", exc)
            return False

    async def _wait_outcome(self, os_id: str) -> BillingOutcome:
        """Verifica se a mensagem de campos obrigatorios surgiu."""
        erro = sefaz_selectors.error_modal(self._page)
        try:
            await erro.wait_for(
                state="visible", timeout=self._settings.result_wait_ms
            )
            logger.warning(
                "OS %s: campos obrigatorios para emitir a NFS-e detectados.", os_id
            )
            return BillingOutcome.ERROR
        except TimeoutError:
            logger.info(
                "OS %s: nenhuma mensagem de erro. OS considerada faturada.", os_id
            )
            return BillingOutcome.SUCCESS

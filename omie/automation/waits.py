"""Esperas explicitas (evitam sleeps fixos sempre que possivel)."""
from __future__ import annotations

from playwright.async_api import Locator, Page, TimeoutError

from omie.services.logger import get_logger
from omie.utils.exceptions import ElementNotFoundError

logger = get_logger(__name__)


class Waits:
    """Helpers de espera explicita sobre uma pagina Playwright."""

    def __init__(self, page: Page, default_timeout_ms: int) -> None:
        self._page = page
        self._default_timeout_ms = default_timeout_ms

    async def visible(
        self,
        locator: Locator,
        *,
        timeout: int | None = None,
        description: str = "elemento",
    ) -> Locator:
        """Aguarda o elemento ficar visivel e o retorna."""
        ms = timeout or self._default_timeout_ms
        try:
            await locator.wait_for(state="visible", timeout=ms)
        except TimeoutError as exc:
            raise ElementNotFoundError(
                f"{description} nao ficou visivel em {ms}ms"
            ) from exc
        return locator

    async def hidden(
        self,
        locator: Locator,
        *,
        timeout: int | None = None,
        description: str = "elemento",
    ) -> None:
        """Aguarda o elemento ficar oculto."""
        ms = timeout or self._default_timeout_ms
        try:
            await locator.wait_for(state="hidden", timeout=ms)
        except TimeoutError as exc:
            raise ElementNotFoundError(
                f"{description} nao ficou oculto em {ms}ms"
            ) from exc

    async def attached(
        self,
        locator: Locator,
        *,
        timeout: int | None = None,
        description: str = "elemento",
    ) -> Locator | None:
        """Aguarda o elemento existir no DOM.

        Returns:
            O elemento ou ``None`` se nao existir dentro do timeout.
        """
        ms = timeout or self._default_timeout_ms
        try:
            await locator.wait_for(state="attached", timeout=ms)
            return locator
        except TimeoutError:
            logger.debug("%s nao foi encontrado no DOM em %dms", description, ms)
            return None

    async def for_timeout(self, milliseconds: int) -> None:
        """Espera fixa, usada apenas quando necessario (fallback)."""
        await self._page.wait_for_timeout(milliseconds)

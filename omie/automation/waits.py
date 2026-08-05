"""Esperas explicitas (evitam sleeps fixos sempre que possivel).

Inclui helpers de resiliencia para redes instaveis: espera a rede assentar
(``settle``) antes de interagir e cliques com retry/backoff para erros
transitorios (interceptacao de overlay, elemento stale, timeout).
"""
from __future__ import annotations

from time import monotonic

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

    async def settle(
        self,
        quiet_ms: int = 1200,
        max_wait_ms: int = 15000,
        description: str = "rede",
    ) -> bool:
        """Aguarda a aplicacao assentar (sem novos requests) antes de seguir.

        Com rede lenta, o app dispara XHR/recursos continuamente durante um
        carregamento. Contamos os recursos baixados via ``performance`` e so
        consideramos a tela 'assentada' quando a contagem para de crescer por
        ``quiet_ms`` consecutivos (ou o limite ``max_wait_ms`` e atingido).

        Returns:
            ``True`` se a rede assentou; ``False`` se o tempo limite chegou.
        """
        deadline = monotonic() + max_wait_ms / 1000
        prev: int | None = None
        stable_since: float | None = None
        while monotonic() < deadline:
            try:
                count = await self._page.evaluate(
                    "() => performance.getEntriesByType('resource').length"
                )
            except Exception:
                await self.for_timeout(400)
                continue
            now = monotonic()
            if prev is None or count != prev:
                prev = count
                stable_since = now
            elif now - stable_since >= quiet_ms / 1000:
                logger.debug("Rede assentada (%s).", description)
                return True
            await self.for_timeout(250)
        logger.debug("Rede nao assentou em %dms (%s).", max_wait_ms, description)
        return False

    async def click(
        self,
        locator: Locator,
        *,
        timeout: int | None = None,
        description: str = "elemento",
        retries: int = 3,
    ) -> bool:
        """Clica no elemento com tolerancia a erros transitorios.

        Aguarda o elemento ficar visivel e tenta o clique até ``retries`` vezes,
        com backoff simples, para absorver interceptacoes de overlay, elementos
        stale e rede instavel.

        Returns:
            ``True`` se clicou; ``False`` se esgotou as tentativas.
        """
        ms = timeout or self._default_timeout_ms
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                await locator.first.wait_for(state="visible", timeout=ms)
                await locator.first.click(timeout=ms)
                logger.debug("Clique realizado: %s", description)
                return True
            except Exception as exc:
                last = exc
                logger.warning(
                    "Tentativa %d/%d ao clicar em '%s': %s",
                    attempt,
                    retries,
                    description,
                    exc,
                )
                if attempt < retries:
                    await self.for_timeout(1000 * attempt)
        raise ElementNotFoundError(
            f"Falha ao clicar em '{description}' apos {retries} tentativas"
        ) from last

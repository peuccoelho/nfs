"""Gerenciamento do navegador (Playwright + Chromium)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from omie.config.settings import Settings
from omie.services.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """Inicializa e encerra o navegador usado pela automacao."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._trace_path: Path | None = None
        self.page: Page | None = None

    async def start(self, storage_state: str | None = None) -> Page:
        """Abre o navegador e retorna a pagina principal.

        ``storage_state`` (arquivo JSON do Playwright) pode ser informado para
        reaproveitar uma sessao logada e evitar o login/2FA repetidos.
        """
        self._configure_browsers_path_if_frozen()
        logger.info(
            "Iniciando Chromium (headless=%s)...", self._settings.headless
        )
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless
        )
        self._context = await self._browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900},
            storage_state=storage_state,
        )
        self.page = await self._context.new_page()
        self.page.set_default_timeout(self._settings.timeout_ms)
        self.page.set_default_navigation_timeout(
            self._settings.timeout_ms + 30000
        )
        logger.info("Navegador iniciado.")
        return self.page

    async def save_storage_state(self, path: Path) -> None:
        """Persiste cookies/localStorage para reaproveitamento da sessao."""
        if self._context is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._context.storage_state(path=str(path))
        logger.info("Sessao salva em: %s", path)

    async def stop(self) -> None:
        """Fecha o navegador e libera os recursos."""
        logger.info("Fechando navegador...")
        await self.stop_tracing()
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self.page = None

    async def enable_tracing(self, path: Path) -> None:
        """Ativa a gravacao de trace do Playwright (para o Trace Viewer).

        Deve ser chamado apos ``start()``. O trace registra snapshots do DOM,
        screenshots, console e rede de cada acao.
        """
        if self._context is None:
            return
        await self._context.tracing.start(
            name="omie-simulacao", screenshots=True, snapshots=True, sources=True
        )
        self._trace_path = path
        logger.info("Tracing ativo. Trace sera salvo em: %s", path)

    async def stop_tracing(self) -> None:
        """Encerra o tracing e grava o arquivo ``.zip`` (deve preceder ``stop``)."""
        if self._context is None or self._trace_path is None:
            return
        try:
            await self._context.tracing.stop(path=str(self._trace_path))
            logger.info("Trace salvo em: %s", self._trace_path)
        except Exception as exc:
            logger.warning("Falha ao salvar o trace: %s", exc)
        finally:
            self._trace_path = None

    def _configure_browsers_path_if_frozen(self) -> None:
        """Quando empacotado (.exe), aponta para a pasta local do Chromium."""
        if getattr(sys, "frozen", False):
            pasta = (
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                / "ms-playwright"
            )
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pasta)

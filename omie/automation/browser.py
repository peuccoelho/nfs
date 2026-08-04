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
        self.page: Page | None = None

    async def start(self) -> Page:
        """Abre o navegador e retorna a pagina principal."""
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
        )
        self.page = await self._context.new_page()
        self.page.set_default_timeout(self._settings.timeout_ms)
        logger.info("Navegador iniciado.")
        return self.page

    async def stop(self) -> None:
        """Fecha o navegador e libera os recursos."""
        logger.info("Fechando navegador...")
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self.page = None

    def _configure_browsers_path_if_frozen(self) -> None:
        """Quando empacotado (.exe), aponta para a pasta local do Chromium."""
        if getattr(sys, "frozen", False):
            pasta = (
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                / "ms-playwright"
            )
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pasta)

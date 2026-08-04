"""Captura de screenshots e salvamento do HTML da pagina em caso de erro."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.async_api import Page

from omie.services.logger import get_logger

logger = get_logger(__name__)


def _pasta_destino(base: Path, subpasta: str) -> Path:
    pasta = base / "logs" / subpasta
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


async def capture_screenshot(page: Page, nome: str, base: Path) -> Path:
    """Salva um screenshot full-page da pagina atual."""
    pasta = _pasta_destino(base, "screenshots")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = pasta / f"{nome}_{ts}.png"
    await page.screenshot(path=str(caminho), full_page=True)
    logger.info("Screenshot salvo: %s", caminho)
    return caminho


async def save_page_html(page: Page, nome: str, base: Path) -> Path:
    """Salva o HTML completo da pagina atual."""
    pasta = _pasta_destino(base, "pages")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = pasta / f"{nome}_{ts}.html"
    html = await page.content()
    caminho.write_text(html, encoding="utf-8")
    logger.info("HTML da pagina salvo: %s", caminho)
    return caminho


async def capture_error_snapshot(
    page: Page, nome: str, base: Path
) -> tuple[Path | None, Path | None]:
    """Captura screenshot e HTML da pagina em caso de excecao.

    Nunca levanta excecao: a captura de diagnostico nao deve mascarar o erro
    original da automacao.
    """
    screenshot: Path | None = None
    html: Path | None = None
    try:
        screenshot = await capture_screenshot(page, nome, base)
    except Exception as exc:
        logger.warning("Falha ao capturar screenshot de erro: %s", exc)
    try:
        html = await save_page_html(page, nome, base)
    except Exception as exc:
        logger.warning("Falha ao salvar HTML de erro: %s", exc)
    return screenshot, html

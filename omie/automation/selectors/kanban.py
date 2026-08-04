"""Seletores do Kanban de Ordens de Servico.

ATENCAO: valores padrao razoaveis; confira conforme a estrutura real do
kanban do Omie (classes/atributos podem variar).
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

SOURCE_COLUMN_TITLE = "Ordem de Serviço"
TARGET_COLUMN_TITLE = "Faturado"

# TODO: ajustar para a estrutura real do kanban do Omie.
_COLUMN_XPATH = (
    "//*[contains(@class,'kanban') or contains(@class,'board') or "
    "contains(@class,'swimlane')]"
    "//*[contains(@class,'column') or contains(@class,'lane')]"
    "[.//*[normalize-space(.)='{title}']]"
)

_CARD_SELECTOR = (
    "[class*='card'], [class*='os-item'], "
    "[data-testid*='card'], [draggable='true']"
)


def column(page: Page, title: str) -> Locator:
    """Localiza uma coluna do kanban pelo titulo."""
    return page.locator(_COLUMN_XPATH.format(title=title)).first


def cards(column: Locator) -> Locator:
    """Localiza os cartoes (OS) dentro de uma coluna."""
    return column.locator(_CARD_SELECTOR)

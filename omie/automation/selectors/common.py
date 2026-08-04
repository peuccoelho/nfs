"""Seletores genericos reutilizaveis em varias etapas."""
from __future__ import annotations

from playwright.async_api import Locator, Page


def get_by_text(page: Page, text: str, exact: bool = False) -> Locator:
    """Localiza elementos por texto (combinacao parcial por padrao)."""
    return page.get_by_text(text, exact=exact)


def button(page: Page, name: str, exact: bool = True) -> Locator:
    """Localiza um botao por nome acessivel."""
    return page.get_by_role("button", name=name, exact=exact)


def link(page: Page, name: str, exact: bool = True) -> Locator:
    """Localiza um link por nome acessivel."""
    return page.get_by_role("link", name=name, exact=exact)


def textbox_by_name(page: Page, name: str) -> Locator:
    """Localiza um campo de texto por nome acessivel."""
    return page.get_by_role("textbox", name=name)


def textbox_by_placeholder(page: Page, placeholder: str) -> Locator:
    """Localiza um campo de texto pelo placeholder."""
    return page.get_by_placeholder(placeholder)

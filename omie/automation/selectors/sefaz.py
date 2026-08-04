"""Seletores do fluxo SEFAZ (correcao de informacoes da NFS-e).

ATENCAO: valores padrao razoaveis; confira conforme o DOM real do Omie.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

ERROR_MESSAGE_FULL = (
    "Informações do cliente alguns campos obrigatórios para emitir a "
    "NFS-e não foram preenchidos."
)
# Fragmento usado na deteccao (mais robusto a quebra de texto).
ERROR_MESSAGE_FRAGMENT = "campos obrigatórios para emitir a NFS-e"

BTN_PESQUISAR_SEFAZ = "Pesquisar Sefaz"
BTN_PESQUISAR = "Pesquisar"
BTN_ATUALIZAR = "Atualizar"
BTN_SALVAR = "Salvar"
BTN_FECHAR = "Fechar"

# TODO: ajustar para as linhas de resultado da consulta SEFAZ.
_RESULT_ROW_SELECTOR = (
    "tr:has(button:has-text('Atualizar')), "
    "[class*='resultado'], [class*='result-item'], [class*='row']"
)


def error_modal(page: Page) -> Locator:
    """Mensagem de campos obrigatorios exibida apos mover a OS."""
    return page.get_by_text(ERROR_MESSAGE_FRAGMENT, exact=False).first


def pesquisar_sefaz_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BTN_PESQUISAR_SEFAZ, exact=True)


def pesquisar_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BTN_PESQUISAR, exact=True)


def atualizar_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BTN_ATUALIZAR, exact=True)


def salvar_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BTN_SALVAR, exact=True)


def close_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BTN_FECHAR, exact=True)


def result_rows(page: Page) -> Locator:
    """Linhas/registros retornados pela consulta SEFAZ."""
    return page.locator(_RESULT_ROW_SELECTOR)

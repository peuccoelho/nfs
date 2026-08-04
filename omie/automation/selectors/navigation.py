"""Seletores de navegacao (selecao de empresa e acesso ao modulo NFS-e).

ATENCAO: valores padrao razoaveis; confira conforme o DOM real do Omie.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

COMPANY_ACCESS_BUTTON = "Acessar"
MENU_SERVICOS = "Serviços"
MENU_NFSE = "NFS-e"
KANBAN_TOGGLE_TEXT = "Exibir etapas das ordens de serviço"


def company_card(page: Page, nome_empresa: str) -> Locator:
    """Localiza o cartao da empresa pelo nome."""
    # TODO: ajustar para a estrutura real da tela de selecao de empresa.
    return page.locator(
        "//*[contains(@class,'empresa') or contains(@class,'company')]"
        "[.//*[normalize-space(text())='{0}']]".format(nome_empresa)
    ).first


def access_button_for_company(page: Page, nome_empresa: str) -> Locator:
    """Localiza o botao 'Acessar' do cartao da empresa."""
    return company_card(page, nome_empresa).get_by_role(
        "button", name=COMPANY_ACCESS_BUTTON, exact=True
    )


def menu_item(page: Page, nome: str) -> Locator:
    """Localiza um item de menu pelo texto."""
    return page.get_by_text(nome, exact=True).first


def kanban_toggle(page: Page) -> Locator:
    """Opcao 'Exibir etapas das ordens de servico'."""
    return page.get_by_text(KANBAN_TOGGLE_TEXT, exact=False)

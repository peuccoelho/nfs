"""Seletores de navegacao (selecao de empresa e acesso a lista de OS).

Confirmados via Codegen no fluxo real do Omie:
    - botao 'Acessar' do cartao de empresa abre o app em nova aba;
    - no app: botao 'Depois' (onboarding) + link 'Servicos e NFS-e' + link
      'Listar todas as'.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

COMPANY_ACCESS_BUTTON = "Acessar"
MENU_SERVICOS = "Serviços e NFS-e"
OS_LIST_LINK = "Listar todas as"
ONBOARDING_LATER_BUTTON = "Depois"


def company_card(page: Page, nome_empresa: str) -> Locator:
    """Localiza o cartao da empresa (portal de apps).

    Escopamos pelo texto/nome via avatar e subimos ate o ancestral que contem o
    botao 'Acessar'.
    """
    return (
        page.get_by_text(nome_empresa, exact=True)
        .locator("xpath=ancestor::*[.//button[normalize-space(.)='Acessar']][1]")
        .first
    )


def access_button_for_company(page: Page, nome_empresa: str) -> Locator:
    """Localiza o botao 'Acessar' do cartao da empresa."""
    return company_card(page, nome_empresa).get_by_role(
        "button", name=COMPANY_ACCESS_BUTTON, exact=True
    )


def onboarding_later_button(page: Page) -> Locator:
    """Botao 'Depois' para fechar o tour/onboarding do app."""
    return page.get_by_role("button", name=ONBOARDING_LATER_BUTTON, exact=True)


def servicos_menu_link(page: Page) -> Locator:
    """Link de menu 'Servicos e NFS-e'."""
    return page.get_by_role("link", name=MENU_SERVICOS).first


def os_list_link(page: Page) -> Locator:
    """Link 'Listar todas as' (listagem de ordens de servico)."""
    return page.get_by_role("link", name=OS_LIST_LINK).first
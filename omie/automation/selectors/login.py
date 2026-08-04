"""Seletores da tela de login do portal Omie.

ATENCAO: os seletores abaixo sao valores padrao razoaveis para o portal
Omie (app.omie.com.br) e devem ser conferidos/ajustados conforme o DOM real.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

from omie.automation.selectors import common

# TODO: conferir os seletores reais do portal Omie.
EMAIL_INPUT_SELECTOR = "input[type='email'], input[placeholder*='e-mail' i]"
PASSWORD_INPUT_SELECTOR = "input[type='password']"

# TODO: nome dos botoes conforme o DOM real (login pode ser em 1 ou 2 etapas).
SUBMIT_BUTTON_NAMES: tuple[str, ...] = ("Entrar", "Acessar", "Entrar no Omie")
CONTINUE_BUTTON_NAMES: tuple[str, ...] = ("Continuar", "Avançar", "Próximo")

# TODO: campo do codigo de verificacao (autenticador/SMS/email).
TWO_FACTOR_INPUT_SELECTOR = (
    "input[placeholder*='código' i], "
    "input[placeholder*='codigo' i], "
    "input[inputmode='numeric']"
)

# TODO: seletor de algo presente apenas quando o usuario esta logado
# (menu lateral, avatar, etc.). Alternativa: aguardar a URL.
APP_HOME_SELECTOR = (
    "[class*='menu-app'], [class*='side-menu'], "
    "[data-testid*='home'], .omie-app"
)


def email_input(page: Page) -> Locator:
    return page.locator(EMAIL_INPUT_SELECTOR).first


def password_input(page: Page) -> Locator:
    return page.locator(PASSWORD_INPUT_SELECTOR).first


def submit_button(page: Page) -> Locator:
    loc = common.button(page, SUBMIT_BUTTON_NAMES[0], exact=True)
    for nome in SUBMIT_BUTTON_NAMES[1:]:
        loc = loc.or_(common.button(page, nome, exact=True))
    return loc


def continue_button(page: Page) -> Locator:
    loc = common.button(page, CONTINUE_BUTTON_NAMES[0], exact=True)
    for nome in CONTINUE_BUTTON_NAMES[1:]:
        loc = loc.or_(common.button(page, nome, exact=True))
    return loc


def two_factor_input(page: Page) -> Locator:
    return page.locator(TWO_FACTOR_INPUT_SELECTOR).first


def two_factor_submit(page: Page) -> Locator:
    return submit_button(page)


def app_home_marker(page: Page) -> Locator:
    return page.locator(APP_HOME_SELECTOR).first

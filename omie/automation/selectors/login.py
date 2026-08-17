"""Seletores da tela de login do portal Omie (fluxo real confirmado via Codegen), caso o fluxo seja unico."""
from __future__ import annotations

from playwright.async_api import Locator, Page

from omie.automation.selectors import common

# Fluxo real do login (app.omie.com.br/login):
#   1. e-mail -> Continuar
#   2. senha -> Entrar 
#   3. codigo 2FA -> Validar
EMAIL_INPUT_SELECTOR = "input[type='email'], input[placeholder*='e-mail' i], input[placeholder*='email' i]"
PASSWORD_INPUT_SELECTOR = "input[type='password']"

SUBMIT_BUTTON_NAMES: tuple[str, ...] = ("Entrar",)
CONTINUE_BUTTON_NAMES: tuple[str, ...] = ("Continuar",)
VALIDATE_BUTTON_NAME = "Validar"

TWO_FACTOR_INPUT_SELECTOR = (
    "input[placeholder*='código' i], "
    "input[placeholder*='codigo' i], "
    "input[inputmode='numeric']"
)

APP_HOME_SELECTOR = (
    "[class*='menu-app'], [class*='side-menu'], "
    "[data-testid*='home'], .omie-app"
)


def email_input(page: Page) -> Locator:
    return page.locator(EMAIL_INPUT_SELECTOR).first


def email_textbox(page: Page) -> Locator:
    return page.get_by_role("textbox", name="Digite seu endereço de e-mail").first


def password_input(page: Page) -> Locator:
    return page.locator(PASSWORD_INPUT_SELECTOR).first


def password_textbox(page: Page) -> Locator:
    return page.get_by_role("textbox", name="Digite aqui sua senha").first


def submit_button(page: Page) -> Locator:
    return common.button(page, SUBMIT_BUTTON_NAMES[0], exact=True)


def continue_button(page: Page) -> Locator:
    return common.button(page, CONTINUE_BUTTON_NAMES[0], exact=True)


def two_factor_input(page: Page) -> Locator:
    # O campo real tem role spinbutton (campo numerico de 1 digito por vez).
    return page.get_by_role("spinbutton", name="Digite o código de segurança").first


def two_factor_submit(page: Page) -> Locator:
    return common.button(page, VALIDATE_BUTTON_NAME, exact=True)


def app_home_marker(page: Page) -> Locator:
    return page.locator(APP_HOME_SELECTOR).first

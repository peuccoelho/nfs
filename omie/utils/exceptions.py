"""Excecoes especificas da automacao.

Hierarquia unica para que o tratamento de erros seja consistente em toda a
aplicacao (captura de screenshot/HTML e registro do passo em andamento).
"""
from __future__ import annotations


class AutomationError(Exception):
    """Excecao base de toda a automacao."""


class ConfigError(AutomationError):
    """Configuracao invalida ou incompleta."""


class CredentialsError(ConfigError):
    """Credenciais ausentes ou invalidas."""


class LoginError(AutomationError):
    """Falha ao realizar o login no portal."""


class TwoFactorError(AutomationError):
    """Falha na autenticacao em dois fatores."""


class NavigationError(AutomationError):
    """Falha durante a navegacao."""


class ElementNotFoundError(AutomationError):
    """Elemento esperado nao foi encontrado na pagina."""


class BillingError(AutomationError):
    """Falha ao faturar uma ordem de servico."""


class SefazError(AutomationError):
    """Falha ao atualizar informacoes via consulta SEFAZ."""


class RetryExhaustedError(AutomationError):
    """Numero maximo de tentativas foi atingido."""

"""Seletores do fluxo de faturamento da lista de Ordens de Servico.

Fluxo real confirmado via Codegen:
    - linha/celula com status 'Aguardando faturamento';
    - 'Faturar Agora' -> confirmar 'Sim';
    - se campos obrigatorios faltando: 'Pesquisar SEFAZ' -> 'Pesquisar' ->
      'Atualizar as informacoes' -> 'Salvar' -> fechar dialogo -> 'Tentar
      Novamente'.

Quando uma nova div de dialogo abre, ela fica por cima (ultima no DOM).
Escopamos as acoes ao dialogo mais a frente para nunca clicar em elementos das
telas de fundo.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

AGUARDANDO_STATUS = "Aguardando faturamento"
FATURAR_AGORA = "Faturar Agora"
CONFIRMAR_SIM = "Sim"

# SEFAZ
PESQUISAR_SEFAZ = "Pesquisar SEFAZ"
PESQUISAR = "Pesquisar"
ATUALIZAR_INFORMACOES = "Atualizar as informações"
SALVAR = "Salvar"
FECHAR = "Fechar"
TENTAR_NOVAMENTE = "Tentar Novamente"

# Fragmento da mensagem de campos obrigatorios.
ERROR_FIELDS_FRAGMENT = "Alguns campos obrigatórios"
# Mensagem de item especifico faltando (nao resolve via SEFAZ -> pular a OS).
ERROR_ITEM_FRAGMENT = "Para emitir a NFS-e falta preencher"
# Mensagem de OS ja faturada (nao faturavel -> pular para a proxima).
ERROR_ALREADY_FATURADA_FRAGMENT = "já foi faturada"


def error_item_message(page: Page) -> Locator:
    """Mensagem 'Para emitir a NFS-e falta preencher o ...' (nao via SEFAZ).

    Indica que um item especifico do cliente esta faltando; nao e resolvido
    pelo SEFAZ. Nesse caso a OS deve ser pulada (fechar e ir para a proxima).
    """
    return page.locator(f"text={ERROR_ITEM_FRAGMENT}")


def already_faturada_message(page: Page) -> Locator:
    """Mensagem de que a OS ja foi faturada (nao faturavel novamente)."""
    return page.locator(f"text={ERROR_ALREADY_FATURADA_FRAGMENT}")


def notif_close(page: Page) -> Locator:
    """Botao de fechar de uma notificacao/toast ``noty`` (se houver)."""
    return page.locator(".noty_bar").get_by_role("button", name=FECHAR).first


def notif_modal(page: Page) -> Locator:
    """Overlay de notificacao ``noty`` que intercepta cliques no fundo."""
    return page.locator(".noty_modal:visible").first


def front_dialog(page: Page) -> Locator:
    """Div de dialogo mais a frente (visivel e ultima no DOM).

    E o dialogo que acabou de abrir; e nele que devem ser feitas as proximas
    acoes, e nao na pagina/dialogo de tras.
    """
    return page.locator("[id^='dialog-outer-wrapper-']:visible").last


def aguardando_cells(page: Page) -> Locator:
    """Celulas de OS que estao 'Aguardando faturamento' no dialogo da frente."""
    return front_dialog(page).get_by_role("cell", name=AGUARDANDO_STATUS)


def row_of(cell: Locator) -> Locator:
    """Linha (``tr``) que contem uma celula."""
    return cell.locator("xpath=ancestor::tr[1]")


def faturar_agora(page: Page) -> Locator:
    return page.get_by_role("link", name=FATURAR_AGORA)


def confirm_sim(page: Page) -> Locator:
    return page.get_by_role("button", name=CONFIRMAR_SIM)


def error_required_link(page: Page) -> Locator:
    """Link da mensagem 'Alguns campos obrigatorios' no dialogo da frente."""
    return front_dialog(page).locator("a").filter(has_text=ERROR_FIELDS_FRAGMENT)


def pesquisar_sefaz_link(page: Page) -> Locator:
    return front_dialog(page).locator("a").filter(has_text=PESQUISAR_SEFAZ)


def pesquisar_button(page: Page) -> Locator:
    return front_dialog(page).get_by_role("button", name=PESQUISAR)


def atualizar_button(page: Page) -> Locator:
    return front_dialog(page).get_by_role("button", name=ATUALIZAR_INFORMACOES)


def salvar_link(page: Page) -> Locator:
    return front_dialog(page).get_by_role("link", name=SALVAR)


def dialog_close(page: Page) -> Locator:
    """Botao 'Fechar' dentro de um dialogo: `#dialog-*`."""
    return page.locator("[id^='dialog-']").get_by_role("button", name=FECHAR)


def sefaz_close(page: Page) -> Locator:
    """Botao 'Fechar' dentro do dialogo mais a frente (SEFAZ)."""
    return front_dialog(page).get_by_role("button", name=FECHAR)


def error_dialog(page: Page) -> Locator:
    """Dialogo atual que exibe a mensagem de campos obrigatorios.

    Escopado pelo link 'Alguns campos obrigatorios' (que so existe nesse
    dialogo), em vez de confiar apenas no `front_dialog`, para nunca mirar a
    tela de fundo.
    """
    return page.locator("a").filter(has_text=ERROR_FIELDS_FRAGMENT).locator(
        "xpath=ancestor::*[starts-with(@id,'dialog-')][1]"
    )


def error_dialog_close(page: Page) -> Locator:
    """Botao 'Fechar' do dialogo de erro atual (caso 'pulada').

    Fluxo confirmado via Codegen: `#dialog-* get_by_role('button', 'Fechar')`.
    """
    return error_dialog(page).get_by_role("button", name=FECHAR)


def tentar_novamente(page: Page) -> Locator:
    return front_dialog(page).get_by_role("button", name=TENTAR_NOVAMENTE)

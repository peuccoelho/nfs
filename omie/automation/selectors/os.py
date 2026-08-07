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
# Mensagem de Codigo NBS obrigatorio nao preenchido (nao resolve via SEFAZ).
ERROR_NBS_FRAGMENT = "Código NBS não foi informado"


def error_item_message(page: Page) -> Locator:
    """Mensagem 'Para emitir a NFS-e falta preencher o ...' (nao via SEFAZ).

    Indica que um item especifico do cliente esta faltando; nao e resolvido
    pelo SEFAZ. Nesse caso a OS deve ser pulada (fechar e ir para a proxima).
    """
    return page.locator(f"text={ERROR_ITEM_FRAGMENT}")


def error_item_link(page: Page) -> Locator:
    """Link 'Para emitir a NFS-e falta preencher...' no dialogo da frente.

    Fluxo manual confirmado: apos 'Sim', esse link aparece no dialogo
    'Conferindo'; clicar nele abre o detalhe do item faltante (que se fecha com
    'Fechar') e entao fecha-se o dialogo atual, pulando a OS.
    """
    return page.locator("a").filter(has_text=ERROR_ITEM_FRAGMENT).first


def already_faturada_message(page: Page) -> Locator:
    """Mensagem de que a OS ja foi faturada (nao faturavel novamente)."""
    return page.locator(f"text={ERROR_ALREADY_FATURADA_FRAGMENT}")


def nbs_error_message(page: Page) -> Locator:
    """Mensagem de que o Codigo NBS e obrigatorio e nao foi preenchido.

    Nao e resolvido via SEFAZ; a OS deve ser pulada (fechar e ir para a
    proxima).
    """
    return page.locator(f"text={ERROR_NBS_FRAGMENT}")


CONFERINDO_FRAGMENT = "Conferindo a Ordem de Servi"


def conferindo_dialog(page: Page) -> Locator:
    """Dialogo 'Conferindo a Ordem de Servico' (checklist de faturamento).

    Abre apos confirmar com 'Sim' e faz checagens (certificado NFS-e, dados do
    cliente, itens, detalhes da prefeitura). Exige um clique em 'OK' para
    prosseguir com a emissao.
    """
    return front_dialog(page).filter(has_text=CONFERINDO_FRAGMENT)


def conferindo_ok_button(page: Page) -> Locator:
    """Botao/link 'OK' (verde) do dialogo 'Conferindo a Ordem de Servico'."""
    return conferindo_dialog(page).get_by_text("OK", exact=True).first


def any_error_message(page: Page) -> Locator:
    """Uniao de todas as mensagens de erro conhecidas do faturamento.

    Seletor somente-CSS (sem misturar engine ``text=``): o item/falta-e-campos
    sao links ``a`` e os demais sao textos.

    Permite aguardar uma unica vez por qualquer dos erros (em vez de checagens
    sequenciais que podem perder o aparecimento tardio do dialogo).
    """
    return page.locator(
        f"a:has-text('{ERROR_ITEM_FRAGMENT}'), "
        f"a:has-text('{ERROR_FIELDS_FRAGMENT}'), "
        f":has-text('{ERROR_ALREADY_FATURADA_FRAGMENT}'), "
        f":has-text('{ERROR_NBS_FRAGMENT}')"
    )


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


FILTRO_SITUACAO_CLASS = "SITUACAO"


def situacao_filter_input(page: Page) -> Locator:
    """Campo de texto do filtro da coluna 'Situacao' (linha de filtro da grade).

    Confirmado via Codegen: a linha ``tr.ui-iggrid-filterrow`` tem uma celula
    ``td.ui-iggrid-filtercell.SITUACAO`` cujo ``input.ui-iggrid-filtereditor``
    recebe o texto do filtro (digitar 'aguardando' + Enter).
    """
    return front_dialog(page).locator(
        "td.ui-iggrid-filtercell.SITUACAO input.ui-igedit-field, "
        "td.ui-iggrid-filtercell.SITUACAO input.ui-iggrid-filtereditor"
    ).first


def situacao_filter_dropdown(page: Page) -> Locator:
    """Botao de operador do filtro de situacao (opcional)."""
    return front_dialog(page).locator(
        "td.ui-iggrid-filtercell.SITUACAO .ui-iggrid-filterbutton"
    ).first


def row_of(cell: Locator) -> Locator:
    """Linha (``tr``) que contem uma celula."""
    return cell.locator("xpath=ancestor::tr[1]")


def os_number_cell(cell: Locator) -> Locator:
    """Celula da coluna 'Número' (id da OS) da linha que contem ``cell``.

    Identifica a coluna pelo cabecalho da grade (`th[id$='_NUMERO']`) e
    seleciona a celula com o mesmo indice na linha. Isso evita depender do
    texto completo da linha (que tambem contem o valor em R$ e pode capturar
    o numero errado).
    """
    row = row_of(cell)
    grid = row.locator(
        "xpath=ancestor::div[contains(@class,'ui-iggrid')][1]"
    )
    header = grid.locator(
        "[class*='ui-iggrid-headertable'] th[id$='_NUMERO']"
    ).first
    index = header.evaluate(
        "headerEl => Array.from(headerEl.parentElement.children).indexOf(headerEl)"
    )
    return row.locator("td").nth(index)


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

"""Correcao de informacoes da NFS-e via consulta SEFAZ."""
from __future__ import annotations

from playwright.async_api import Page, TimeoutError

from omie.automation.selectors import sefaz as sefaz_selectors
from omie.automation.waits import Waits
from omie.services.logger import get_logger

logger = get_logger(__name__)


class SefazUpdater:
    """Executa o fluxo 'Pesquisar Sefaz' para corrigir a OS e voltar ao kanban."""

    def __init__(self, page: Page, waits: Waits, recorder: object | None = None) -> None:
        self._page = page
        self._waits = waits
        self._recorder = recorder

    async def fix_and_return(self) -> None:
        """Executa o procedimento completo de atualizacao via SEFAZ."""
        logger.info("Iniciando correcao via SEFAZ...")
        await self._capture("sefaz_erro")
        await self._open_sefaz_search()
        await self._capture("sefaz_aberto")
        await self._run_search()
        await self._capture("sefaz_resultados")
        await self._update_all_results()
        await self._capture("sefaz_atualizado")
        await self._save()
        await self._capture("sefaz_salvo")
        await self._close_and_return()
        await self._capture("sefaz_fechado")
        logger.info("Correcao via SEFAZ concluida.")

    async def _capture(self, nome: str) -> None:
        if self._recorder is not None:
            try:
                await self._recorder.capture(nome, self._page)
            except Exception as exc:
                logger.warning("Falha ao capturar '%s': %s", nome, exc)

    async def _open_sefaz_search(self) -> None:
        """Clica em 'Pesquisar Sefaz' (janela de erro da NFS-e)."""
        botao = sefaz_selectors.pesquisar_sefaz_button(self._page)
        await self._waits.visible(
            botao, timeout=15000, description="botao 'Pesquisar Sefaz'"
        )
        await botao.first.click()
        await self._waits.for_timeout(1500)

    async def _run_search(self) -> None:
        """Clica em 'Pesquisar' e aguarda os resultados da consulta."""
        botao = sefaz_selectors.pesquisar_button(self._page)
        await self._waits.visible(
            botao, timeout=15000, description="botao 'Pesquisar'"
        )
        await botao.first.click()
        await self._waits.for_timeout(3000)

        linhas = sefaz_selectors.result_rows(self._page)
        try:
            await linhas.first.wait_for(state="visible", timeout=20000)
            logger.info("Resultados da consulta SEFAZ exibidos.")
        except TimeoutError:
            logger.warning("Nenhum resultado retornado pela consulta SEFAZ.")

    async def _update_all_results(self) -> None:
        """Atualiza todas as informacoes retornadas pela SEFAZ."""
        linhas = sefaz_selectors.result_rows(self._page)
        total = await linhas.count()
        for indice in range(total):
            botao = linhas.nth(indice).get_by_role(
                "button", name=sefaz_selectors.BTN_ATUALIZAR, exact=True
            )
            try:
                if await botao.count() and await botao.first.is_visible(timeout=2000):
                    await botao.first.click()
                    await self._waits.for_timeout(800)
                    logger.info(
                        "Informacoes atualizadas para o resultado %d/%d.",
                        indice + 1, total,
                    )
            except Exception as exc:
                logger.warning("Falha ao atualizar resultado %d: %s", indice + 1, exc)

        if total == 0:
            botao = sefaz_selectors.atualizar_button(self._page)
            try:
                if await botao.count() and await botao.first.is_visible(timeout=2000):
                    await botao.first.click()
                    await self._waits.for_timeout(800)
                    logger.info("Informacoes atualizadas (botao global).")
            except Exception as exc:
                logger.warning("Botao 'Atualizar' global nao disponivel: %s", exc)

    async def _save(self) -> None:
        """Salva as informacoes atualizadas."""
        botao = sefaz_selectors.salvar_button(self._page)
        await self._waits.visible(botao, timeout=15000, description="botao 'Salvar'")
        await botao.first.click()
        await self._waits.for_timeout(1500)

    async def _close_and_return(self) -> None:
        """Fecha janelas/popups extras e retorna ao kanban."""
        for popup in self._page.context.pages:
            if popup != self._page:
                await popup.close()

        fechar = sefaz_selectors.close_button(self._page)
        try:
            if await fechar.count() and await fechar.first.is_visible(timeout=2500):
                await fechar.first.click()
                await self._waits.for_timeout(1000)
        except Exception:
            pass

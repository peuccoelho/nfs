"""Faturamento em looping das Ordens de Servico.

Processa todas as OS com status 'Aguardando faturamento' na listagem, uma a
uma: Faturar Agora -> confirmar -> (correcao SEFAZ se campos faltando) -> volta
para a lista. Encerra quando nao restar nenhuma OS aguardando.
"""
from __future__ import annotations

import re

from playwright.async_api import Locator, Page, TimeoutError

from omie.automation.selectors import navigation as nav_selectors
from omie.automation.selectors import os as os_selectors
from omie.automation.waits import Waits
from omie.config.settings import Settings
from omie.services.logger import get_logger
from omie.services.report import WorkOrderResult

logger = get_logger(__name__)

MAX_TENTATIVAS = 3


class OSService:
    """Fatura todas as OS 'Aguardando faturamento' da lista, em loop."""

    def __init__(
        self,
        page: Page,
        settings: Settings,
        waits: Waits,
        recorder: object | None = None,
        dry_run: bool = False,
    ) -> None:
        self._page = page
        self._settings = settings
        self._waits = waits
        self._recorder = recorder
        self._dry_run = dry_run
        self._puladas: set[str] = set()

    async def process_all(self) -> list[WorkOrderResult]:
        """Processa todas as OS aguardando e retorna o resumo."""
        resultados: list[WorkOrderResult] = []
        tentativas: dict[str, int] = {}
        logger.info("Iniciando loop de faturamento de OS.")
        primeira_vez = True

        while True:
            if not primeira_vez:
                await self._refresh_list()
            primeira_vez = False
            try:
                cell = await self._next_aguardando()
            except Exception as exc:
                logger.warning("Pagina indisponivel durante o loop: %s", exc)
                break
            if cell is None:
                logger.info(
                    "Nenhuma OS 'Aguardando faturamento' restante. Encerrando."
                )
                break

            os_id = await self._extract_os_id(cell)
            logger.info("OS %s localizada (aguardando faturamento).", os_id)
            await self._capture("os_inicio")

            if self._dry_run:
                await self._capture("os_dry_run")
                resultados.append(self._result(os_id, "simulada", error="dry-run"))
                continue

            tentativa = tentativas.get(os_id, 0)
            if tentativa >= MAX_TENTATIVAS:
                logger.warning(
                    "OS %s atingiu o maximo de %d tentativas; registrando falha.",
                    os_id,
                    MAX_TENTATIVAS,
                )
                resultados.append(
                    self._result(
                        os_id, "failure", error="maximo de tentativas atingido"
                    )
                )
                tentativas[os_id] = tentativa + 1
                continue

            resultado = await self._bill_one(cell, os_id)
            tentativas[os_id] = tentativa + 1
            resultados.append(resultado)

        logger.info(
            "Processamento concluido: %d OS (sucesso=%d, via SEFAZ=%d, puladas=%d).",
            len(resultados),
            sum(1 for r in resultados if r.status == "success"),
            sum(1 for r in resultados if r.status == "via_sefaz"),
            sum(1 for r in resultados if r.status == "pulada"),
        )
        return resultados

    async def _refresh_list(self) -> None:
        """Deixa a listagem de OS pronta para a proxima OS a faturar.

        Apos uma OS 'pulada', o app **volta para a lista** ao fechar o dialogo
        de erro; nesse caso nao ha menu para reabrir. Apos um faturamento
        **com sucesso**, o app redireciona para o menu e e preciso reabrir a
        listagem ('Listar todas as'), aguardando o app assentar.
        """
        await self._waits.settle(quiet_ms=1000, max_wait_ms=12000, description="pos-acao")
        cells = os_selectors.aguardando_cells(self._page)
        try:
            await cells.first.wait_for(state="visible", timeout=6000)
            logger.info("Lista ja visivel (caso pulada); seguindo direto.")
            await self._waits.for_timeout(1000)
            return
        except TimeoutError:
            pass

        await self._waits.settle(quiet_ms=1000, max_wait_ms=20000, description="menu")
        try:
            await self._close_leftover_dialogs()
            link_lista = nav_selectors.os_list_link(self._page)
            try:
                await link_lista.first.wait_for(state="visible", timeout=20000)
            except TimeoutError:
                logger.info("Submenu recolhido; expandindo 'Servicos e NFS-e'...")
                serv = nav_selectors.servicos_menu_link(self._page)
                await serv.first.wait_for(state="visible", timeout=30000)
                await self._waits.click(
                    serv, timeout=15000, description="menu 'Servicos e NFS-e'"
                )
                await self._waits.for_timeout(2000)
                await link_lista.first.wait_for(state="visible", timeout=20000)
            await self._waits.click(
                link_lista, timeout=20000, description="link 'Listar todas as'"
            )
            await self._waits.settle(
                quiet_ms=1000, max_wait_ms=25000, description="lista"
            )
            cells = os_selectors.aguardando_cells(self._page)
            await cells.first.wait_for(state="attached", timeout=30000)
        except Exception as exc:
            logger.warning("Nao foi possivel reabrir a listagem: %s", exc)

    async def _close_leftover_dialogs(self) -> None:
        """Fecha dialogos residuais que cubram o menu antes de reabrir a lista."""
        for _ in range(5):
            fechar = os_selectors.sefaz_close(self._page)
            try:
                if await fechar.count() and await fechar.is_visible(timeout=1500):
                    await fechar.click(timeout=5000)
                    await self._waits.for_timeout(1500)
                else:
                    return
            except Exception as exc:
                logger.warning("Falha ao fechar dialogo residual: %s", exc)
                return

    async def _next_aguardando(self) -> Locator | None:
        """Retorna a primeira celula 'Aguardando faturamento' nao pulada."""
        cells = os_selectors.aguardando_cells(self._page)
        try:
            await cells.first.wait_for(state="attached", timeout=30000)
        except TimeoutError:
            return None
        total = await cells.count()
        for i in range(total):
            cell = cells.nth(i)
            try:
                if not await cell.is_visible(timeout=2000):
                    continue
                os_id = await self._extract_os_id(cell)
                if os_id in self._puladas:
                    logger.debug("OS %s ja pulada; ignorando.", os_id)
                    continue
                return cell
            except Exception:
                continue
        return None

    async def _bill_one(self, cell: Locator, os_id: str) -> WorkOrderResult:
        """Fatura uma OS (com correcao SEFAZ se necessario)."""
        try:
            await self._waits.click(
                cell, timeout=20000, description=f"celula da OS {os_id}"
            )
            await self._waits.visible(
                os_selectors.faturar_agora(self._page),
                timeout=30000,
                description="botao 'Faturar Agora'",
            )
            await self._waits.click(
                os_selectors.faturar_agora(self._page),
                timeout=20000,
                description="botao 'Faturar Agora'",
            )
            await self._waits.settle(
                quiet_ms=1000, max_wait_ms=10000, description="pos-faturar-agora"
            )

            await self._waits.visible(
                os_selectors.confirm_sim(self._page),
                timeout=30000,
                description="confirmacao 'Sim'",
            )
            await self._waits.click(
                os_selectors.confirm_sim(self._page),
                timeout=20000,
                description="confirmacao 'Sim'",
            )
            await self._waits.settle(
                quiet_ms=1200, max_wait_ms=15000, description="resultado do billing"
            )
            await self._capture("faturado")

            if await self._required_fields_error(timeout=4000):
                resolvido = await self._sefaz_correction()
                if resolvido:
                    status = "via_sefaz"
                else:
                    status = "pulada"
                    self._puladas.add(os_id)
            elif await self._error_item_message(timeout=4000):
                logger.warning(
                    "OS %s: item especifico faltando (nao via SEFAZ); pulando.",
                    os_id,
                )
                await self._click_if_visible(
                    os_selectors.sefaz_close(self._page),
                    "Fechar dialogo (item faltando)",
                )
                status = "pulada"
                self._puladas.add(os_id)
            elif await self._already_faturada_error(timeout=4000):
                logger.warning(
                    "OS %s: ja faturada; pulando para a proxima.", os_id
                )
                await self._close_current_popup()
                status = "pulada"
                self._puladas.add(os_id)
            else:
                status = "success"
            await self._dismiss_notifs()
            return self._result(os_id, status)
        except Exception as exc:
            logger.error("OS %s: falha no faturamento: %s", os_id, exc)
            await self._capture("os_erro")
            return self._result(os_id, "failure", error=str(exc)[:200])

    async def _required_fields_error(self, timeout: int = 8000) -> bool:
        """True se a mensagem de campos obrigatorios apareceu."""
        link = os_selectors.error_required_link(self._page)
        try:
            await link.first.wait_for(state="visible", timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def _error_item_message(self, timeout: int = 8000) -> bool:
        """True se a mensagem de 'item especifico faltando' apareceu."""
        msg = os_selectors.error_item_message(self._page)
        try:
            await msg.first.wait_for(state="visible", timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def _already_faturada_error(self, timeout: int = 8000) -> bool:
        """True se apareceu o aviso de que a OS ja foi faturada."""
        msg = os_selectors.already_faturada_message(self._page)
        try:
            await msg.first.wait_for(state="visible", timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def _close_current_popup(self) -> None:
        """Fecha o dialogo/notificacao atual (botao 'Fechar')."""
        if await self._click_if_visible(
            os_selectors.sefaz_close(self._page),
            "Fechar dialogo popup",
        ):
            return
        if await self._click_if_visible(
            os_selectors.notif_close(self._page),
            "Fechar notificacao (noty)",
        ):
            return

    async def _dismiss_notifs(self) -> None:
        """Dispensa notificacoes ``noty`` que interceptam cliques no fundo.

        Um toast (ex.: 'NFS-e emitida com sucesso', 'OS ja faturada') deixa um
        `.noty_modal` sobre a tela que interceptada os cliques seguintes; fecha-o
        clicando na propria notificacao/fundo.
        """
        for _ in range(3):
            overlay = os_selectors.notif_modal(self._page)
            try:
                if await overlay.count() and await overlay.is_visible(timeout=800):
                    await overlay.click(timeout=3000)
                    await self._waits.for_timeout(1000)
                    continue
            except Exception:
                pass
            fechar = os_selectors.notif_close(self._page)
            try:
                if await fechar.count() and await fechar.is_visible(timeout=800):
                    await fechar.click(timeout=3000)
                return
            except Exception:
                return

    async def _sefaz_correction(self) -> bool:
        """Executa a correcao SEFAZ e 'Tentar Novamente'.

        Fluxo confirmado via Codegen:
            erro 'Alguns campos obrigatorios' -> link do erro ->
            'Pesquisar SEFAZ' -> 'Pesquisar' -> 'Atualizar as informacoes' ->
            'Salvar' -> fechar dialogo -> 'Tentar Novamente'.

        Returns:
            ``True`` se o cliente passou a ter os dados (billing aceito);
            ``False`` se os campos continuam obrigatorios mesmo apos o SEFAZ
            (a OS sera pulada e preenchida manualmente depois).
        """
        logger.info("Campos obrigatorios faltando. Iniciando correcao SEFAZ.")
        await self._capture("sefaz_erro")

        if not await self._click_if_visible(
            os_selectors.error_required_link(self._page), "link de campos obrigatorios"
        ):
            logger.warning("Link de erro nao encontrado; seguindo para SEFAZ.")
        await self._waits.for_timeout(2000)

        if not await self._click_if_visible(
            os_selectors.pesquisar_sefaz_link(self._page), "Pesquisar SEFAZ"
        ):
            return False
        await self._waits.for_timeout(3000)

        if not await self._click_if_visible(
            os_selectors.pesquisar_button(self._page), "Pesquisar"
        ):
            return False
        await self._waits.for_timeout(6000)

        if not await self._click_if_visible(
            os_selectors.atualizar_button(self._page), "Atualizar as informacoes"
        ):
            return False
        await self._waits.for_timeout(2000)

        if not await self._click_if_visible(
            os_selectors.salvar_link(self._page), "Salvar"
        ):
            return False
        await self._waits.for_timeout(3000)
        await self._capture("sefaz_salvo")

        if not await self._click_if_visible(
            os_selectors.sefaz_close(self._page), "Fechar dialogo SEFAZ"
        ):
            logger.warning("Nenhum botao 'Fechar' encontrado no dialogo SEFAZ.")
        await self._waits.for_timeout(2000)
        await self._capture("sefaz_fechado")

        if not await self._click_if_visible(
            os_selectors.tentar_novamente(self._page), "Tentar Novamente"
        ):
            logger.warning("Botao 'Tentar Novamente' nao encontrado.")
        await self._waits.settle(
            quiet_ms=1500, max_wait_ms=25000, description="retentativa de billing"
        )

        resolvido = True
        if await self._error_item_message(timeout=8000):
            resolvido = False
            logger.warning(
                "Item especifico ainda faltando apos o SEFAZ; OS sera pulada "
                "(preenchimento manual depois)."
            )
            await self._click_if_visible(
                os_selectors.sefaz_close(self._page),
                "Fechar dialogo (item faltando)",
            )
        elif await self._required_fields_error(timeout=8000):
            resolvido = False
            logger.warning(
                "Campos continuam obrigatorios mesmo apos o SEFAZ; OS sera "
                "pulada (preenchimento manual depois)."
            )
            await self._click_if_visible(
                os_selectors.error_dialog_close(self._page),
                "Fechar erro residual (botao 'Fechar' do dialogo de erro)",
            )
        if not resolvido:
            await self._waits.for_timeout(2000)
            await self._capture("sefaz_nao_resolvido")
        logger.info("Correcao SEFAZ concluida (resolvido=%s).", resolvido)
        return resolvido

    async def _click_if_visible(self, locator: Locator, desc: str) -> bool:
        """Clica no primeiro elemento visivel do locator, com tolerancia.

        Aguarda ate 30s pelo elemento ficar visivel (dialogos abrem devagar) e
        tenta o clique ate 3x, absorvendo interceptacoes de overlay e rede
        instavel.
        """
        try:
            await locator.first.wait_for(state="visible", timeout=30000)
        except Exception as exc:
            logger.warning("'%s' nao ficou visivel: %s", desc, exc)
            return False
        for tentativa in range(1, 4):
            try:
                await locator.first.click(timeout=10000)
                logger.info("Clique: %s", desc)
                return True
            except Exception as exc:
                logger.warning(
                    "Tentativa %d/3 ao clicar em '%s': %s", tentativa, desc, exc
                )
                await self._waits.for_timeout(1500)
        return False

    async def _extract_os_id(self, cell: Locator) -> str:
        """Tenta extrair o numero da OS a partir do texto da linha."""
        try:
            row = os_selectors.row_of(cell)
            texto = await row.text_content()
            if texto:
                m = re.search(r"\b(\d{3,})\b", texto)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return "desconhecida"

    @staticmethod
    def _result(
        os_id: str, status: str, error: str | None = None
    ) -> WorkOrderResult:
        return WorkOrderResult(
            os_id=os_id,
            status=status,
            attempts=1,
            duration_seconds=0.0,
            error=error,
        )

    async def _capture(self, nome: str) -> None:
        if self._recorder is not None:
            try:
                await self._recorder.capture(nome, self._page)
            except Exception as exc:
                logger.warning("Falha ao capturar '%s': %s", nome, exc)
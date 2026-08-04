"""Processamento continuo do kanban de ordens de servico.

O loop fatura todas as OS da coluna 'Ordem de Serviço', corrigindo via SEFAZ
quando ha campos obrigatorios pendentes e registrando cada resultado. Encerra
apenas quando nao ha mais OS na coluna.
"""
from __future__ import annotations

import re
import time

from playwright.async_api import Locator, Page, TimeoutError

from omie.automation.invoice import BillingOutcome, InvoiceBiller
from omie.automation.selectors import kanban as kanban_selectors
from omie.automation.sefaz import SefazUpdater
from omie.automation.waits import Waits
from omie.config.settings import Settings
from omie.services.logger import get_logger
from omie.services.report import WorkOrderResult

logger = get_logger(__name__)


class KanbanProcessor:
    """Itera por todas as OS da coluna e fatura automaticamente."""

    def __init__(self, page: Page, settings: Settings, waits: Waits) -> None:
        self._page = page
        self._settings = settings
        self._waits = waits
        self._invoice = InvoiceBiller(page, settings, waits)
        self._sefaz = SefazUpdater(page, waits)

    async def process_all(self) -> list[WorkOrderResult]:
        """Processa todas as OS disponiveis na coluna de origem."""
        resultados: list[WorkOrderResult] = []
        logger.info("Iniciando processamento do kanban.")

        iniciais = await kanban_selectors.cards(self._source_column()).count()
        logger.info("Quantidade de OS encontradas na coluna: %d", iniciais)

        while True:
            source = self._source_column()
            card = await self._first_card(source)
            if card is None:
                logger.info(
                    "Nenhuma OS restante na coluna '%s'. Encerrando.",
                    kanban_selectors.SOURCE_COLUMN_TITLE,
                )
                break

            os_id = await self._extract_os_id(card)
            if os_id is None:
                logger.warning(
                    "OS sem identificacao numerica detectada. Seguindo em frente."
                )
                resultados.append(
                    WorkOrderResult(
                        os_id="desconhecida",
                        status="failure",
                        attempts=0,
                        duration_seconds=0.0,
                        error="identificacao da OS nao encontrada",
                    )
                )
                continue

            logger.info("Localizada OS %s na coluna de origem.", os_id)
            resultado = await self._process_one(os_id)
            resultados.append(resultado)
            await self._waits.for_timeout(600)

        logger.info(
            "Processamento concluido: %d OS (sucesso=%d, falhas=%d).",
            len(resultados),
            sum(1 for r in resultados if r.status == "success"),
            sum(1 for r in resultados if r.status == "failure"),
        )
        return resultados

    async def _process_one(self, os_id: str) -> WorkOrderResult:
        """Fatura uma OS com retry (e correcao SEFAZ) ate o limite configurado."""
        inicio = time.perf_counter()
        tentativas = 0
        erro: str | None = None

        logger.info("Iniciando faturamento da OS %s.", os_id)
        for tentativa in range(1, self._settings.retries_max + 1):
            tentativas = tentativa
            resultado = await self._invoice.bill(
                self._source_column(), self._target_column(), os_id
            )

            if resultado is BillingOutcome.SUCCESS:
                logger.info("OS %s faturada com sucesso.", os_id)
                erro = None
                break

            if resultado is BillingOutcome.ERROR:
                erro = "campos obrigatorios da NFS-e nao preenchidos"
                if tentativa < self._settings.retries_max:
                    logger.info(
                        "OS %s: corrigindo via SEFAZ (tentativa %d/%d).",
                        os_id, tentativa, self._settings.retries_max,
                    )
                    await self._sefaz.fix_and_return()
                    await self._waits.for_timeout(1500)
                    continue
                logger.warning("OS %s: limite de tentativas atingido.", os_id)
                break

            erro = "faturamento sem confirmacao (timeout)"
            logger.warning("OS %s: %s", os_id, erro)
            break

        duracao = time.perf_counter() - inicio
        status = "success" if erro is None else "failure"
        logger.info(
            "OS %s: status=%s, tentativas=%d, tempo=%.1fs.",
            os_id, status, tentativas, duracao,
        )
        return WorkOrderResult(
            os_id=os_id,
            status=status,
            attempts=tentativas,
            duration_seconds=round(duracao, 2),
            error=erro,
        )

    async def _first_card(self, column: Locator) -> Locator | None:
        """Retorna o primeiro cartao da coluna, ou ``None``."""
        cards = kanban_selectors.cards(column)
        try:
            await cards.first.wait_for(state="attached", timeout=5000)
        except TimeoutError:
            return None
        return cards.first

    @staticmethod
    async def _extract_os_id(card: Locator) -> str | None:
        """Extrai o numero/identificacao da OS a partir do texto do cartao."""
        texto = await card.text_content()
        if not texto:
            return None
        match = re.search(r"\b(\d{3,})\b", texto)
        return match.group(1) if match else None

    def _source_column(self) -> Locator:
        return kanban_selectors.column(
            self._page, kanban_selectors.SOURCE_COLUMN_TITLE
        )

    def _target_column(self) -> Locator:
        return kanban_selectors.column(
            self._page, kanban_selectors.TARGET_COLUMN_TITLE
        )

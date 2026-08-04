"""Orquestrador da automacao (passos de alto nivel da execucao)."""
from __future__ import annotations

from datetime import datetime

from playwright.async_api import Page

from omie.automation.browser import BrowserManager
from omie.automation.kanban import KanbanProcessor
from omie.automation.login import LoginFlow
from omie.automation.navigation import Navigation
from omie.automation.waits import Waits
from omie.config.credentials import Credentials
from omie.config.settings import Settings
from omie.services.authentication import AuthenticationService
from omie.services.logger import get_logger
from omie.services.report import ExecutionResult
from omie.utils.screenshots import capture_error_snapshot

logger = get_logger(__name__)


class AutomationRunner:
    """Coordenador principal: browser -> login -> empresa -> NFS-e -> kanban."""

    def __init__(self, settings: Settings, credentials: Credentials) -> None:
        self._settings = settings
        self._credentials = credentials
        self._browser = BrowserManager(settings)
        self._page: Page | None = None
        self._current_step = "inicializacao"
        self._result = ExecutionResult(started_at=datetime.now())

    async def run(self) -> ExecutionResult:
        """Executa todo o fluxo e retorna o resumo da execucao.

        Em caso de excecao fatal: salva screenshot + HTML da pagina, registra o
        stacktrace completo e a etapa em andamento, e relanca o erro.
        """
        try:
            self._step("Iniciando navegador")
            self._page = await self._browser.start()
            waits = Waits(self._page, self._settings.timeout_ms)
            authentication = AuthenticationService()

            self._step("Realizando login no Omie")
            await LoginFlow(
                self._page, self._settings, self._credentials, authentication, waits
            ).execute()

            navigation = Navigation(self._page, self._settings, waits)
            self._step("Selecionando empresa")
            await navigation.select_company()

            self._step("Acessando modulo NFS-e / kanban de OS")
            await navigation.go_to_os_kanban()

            self._step("Processando ordens de servico no kanban")
            work_orders = await KanbanProcessor(
                self._page, self._settings, waits
            ).process_all()

            self._result.work_orders = work_orders
            self._result.finished_at = datetime.now()
            self._step(
                f"Processamento finalizado: {self._result.total_os} OS processadas"
            )
            logger.info(
                "Resumo final: %d OS, %d sucesso, %d falhas.",
                self._result.total_os,
                self._result.success_count,
                self._result.failure_count,
            )
            return self._result

        except Exception as exc:
            if self._page is not None:
                await capture_error_snapshot(
                    self._page, "erro_fatal", self._settings.base
                )
            self._result.finished_at = datetime.now()
            logger.error(
                "Falha durante a etapa '%s': %s",
                self._current_step,
                exc,
                exc_info=True,
            )
            raise

        finally:
            await self._browser.stop()

    def _step(self, descricao: str) -> None:
        """Registra a etapa atual no log e no relatorio."""
        self._current_step = descricao
        self._result.step_log.append(descricao)
        logger.info("ETAPA: %s", descricao)

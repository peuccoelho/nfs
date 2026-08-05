"""Orquestrador da automacao (passos de alto nivel da execucao).

Inclui resiliencia a rede instavel: se uma etapa falhar (pagina fechada, timeout
fatal, etc.), o fluxo e reiniciado a partir do navegador, com backoff. Como o
faturamento e idempotente (OS ja faturada sao puladas), reiniciar e seguro.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Page

from omie.automation.browser import BrowserManager
from omie.automation.faturamento import OSService
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
    """Coordenador principal: browser -> login -> empresa -> NFS-e -> OS.

    Aceita um ``recorder`` opcional (observer que registra o fluxo) e um modo
    ``dry_run`` (inspecao sem faturar), usados pela simulacao/inspecao.
    """

    def __init__(
        self,
        settings: Settings,
        credentials: Credentials,
        recorder: Any | None = None,
        dry_run: bool = False,
        trace_path: Path | None = None,
        session_path: Path | None = None,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._recorder = recorder
        self._dry_run = dry_run
        self._trace_path = trace_path
        self._session_path = session_path
        self._browser = BrowserManager(settings)
        self._page: Page | None = None
        self._current_step = "inicializacao"
        self._result = ExecutionResult(started_at=datetime.now())

    async def run(self) -> ExecutionResult:
        """Executa todo o fluxo com retries, retornando o resumo da execucao.

        Se uma tentativa falhar de forma fatal (ex.: a pagina fechou), fecha o
        navegador, aguarda um backoff e reinicia do zero (login com sessao
        persistida e rapido). A flag de que uma OS ja foi faturada torna a
        repeticao segura.
        """
        max_attempts = max(2, self._settings.retries_max)
        try:
            for attempt in range(1, max_attempts + 1):
                self._current_step = "inicializacao"
                try:
                    await self._start_browser(attempt)
                    return await self._attempt_flow()
                except Exception as exc:
                    logger.error(
                        "Tentativa %d/%d falhou na etapa '%s': %s",
                        attempt,
                        max_attempts,
                        self._current_step,
                        exc,
                        exc_info=True,
                    )
                    if self._page is not None:
                        await capture_error_snapshot(
                            self._page,
                            "erro_fatal",
                            self._settings.base,
                        )
                    if attempt >= max_attempts:
                        raise
                    await self._reset_browser()
                    delay = int(self._settings.retry_delay_s * 2 * attempt)
                    logger.info("Reiniciando o fluxo em %ds...", delay)
                    await asyncio.sleep(delay)
            raise RuntimeError("Fluxo encerrado sem concluir")
        finally:
            await self._browser.stop()

    async def _start_browser(self, attempt: int) -> None:
        """Inicia o navegador (e o tracing), reaproveitando a sessao."""
        self._step(f"Iniciando navegador (tentativa {attempt})")
        storage = None
        if self._session_path is not None and self._session_path.exists():
            storage = str(self._session_path)
        self._page = await self._browser.start(storage_state=storage)
        if self._trace_path:
            await self._browser.enable_tracing(self._trace_path)

    async def _attempt_flow(self) -> ExecutionResult:
        """Executa login, navegacao e faturamento em uma mesma tentativa."""
        self._result = ExecutionResult(started_at=datetime.now())
        assert self._page is not None

        waits = Waits(self._page, self._settings.timeout_ms)
        authentication = AuthenticationService()

        await self._capture("login_inicio")
        self._step("Realizando login no Omie")
        await LoginFlow(
            self._page, self._settings, self._credentials, authentication, waits
        ).execute()
        if self._session_path is not None:
            await self._browser.save_storage_state(self._session_path)
        await self._capture("login_fim")

        navigation = Navigation(self._page, self._settings, waits)
        self._step("Selecionando empresa")
        await self._capture("empresa_inicio")
        await navigation.select_company()
        await self._switch_to_app_page()
        # Reconstroi dependencias apontando para a aba do aplicativo.
        waits = Waits(self._page, self._settings.timeout_ms)
        navigation = Navigation(self._page, self._settings, waits)
        # Fecha o tour/onboarding ('Depois') logo apos o app abrir, para
        # nao interceptar cliques posteriores.
        await navigation.dismiss_onboarding()
        await self._capture("empresa_fim")

        self._step("Acessando modulo NFS-e / lista de OS")
        await self._capture("nfse_inicio")
        await navigation.go_to_os_list()
        await self._capture("nfse_fim")

        self._step("Processando ordens de servico aguardando faturamento")
        work_orders = await OSService(
            self._page,
            self._settings,
            waits,
            recorder=self._recorder,
            dry_run=self._dry_run,
        ).process_all()

        self._result.work_orders = work_orders
        self._result.finished_at = datetime.now()
        await self._capture("faturamento_fim")
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

    async def _capture(self, nome: str) -> None:
        """Registra a etapa atual no recorder (se existir)."""
        if self._recorder is not None and self._page is not None:
            try:
                await self._recorder.capture(nome, self._page)
            except Exception as exc:
                logger.warning("Falha ao capturar etapa '%s': %s", nome, exc)

    async def _switch_to_app_page(self) -> None:
        """Aponta o runner para a aba do aplicativo Omie aberta pelo portal."""
        if self._page is None:
            return
        context = self._page.context
        for _ in range(45):
            for page in context.pages:
                if page is self._page:
                    continue
                url = page.url
                if (
                    ("app.omie.com.br" in url or "hype.omie.com.br" in url)
                    and "login" not in url.lower()
                    and "meus-aplicativos" not in url
                ):
                    self._page = page
                    self._page.set_default_timeout(self._settings.timeout_ms)
                    self._page.set_default_navigation_timeout(
                        self._settings.timeout_ms + 30000
                    )
                    logger.info("Aplicativo aberto em nova aba: %s", url)
                    return
            await self._page.wait_for_timeout(1000)
        logger.info(
            "Nenhuma aba nova detectada; mantendo a pagina atual (%s).",
            self._page.url,
        )

    async def _reset_browser(self) -> None:
        """Fecha o navegador atual para que a proxima tentativa recomece."""
        await self._browser.stop()
        self._page = None

    def _step(self, descricao: str) -> None:
        """Registra a etapa atual no log e no relatorio."""
        self._current_step = descricao
        self._result.step_log.append(descricao)
        logger.info("ETAPA: %s", descricao)
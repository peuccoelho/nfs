import asyncio
from datetime import datetime
from pathlib import Path

from playwright.async_api import (
    Download,
    FrameLocator,
    Locator,
    Page,
    Playwright,
    async_playwright,
)

from config import Config
from downloader import processar_download
from utils import (
    criar_diretorio_downloads,
    get_logger,
    split_date_range,
    xml_ja_existe,
)

logger = get_logger(__name__)

URL_LOGIN = "https://nfse2.camacari.ba.gov.br/prefeituras/loginb.tela"
TIMEOUT_PADRAO = 30000
TIMEOUT_CONSULTA = 60000
TIMEOUT_TABELA = 15000


class PortalNFSE:
    """Automacao do portal de NFS-e da Prefeitura de Camacari."""

    def __init__(self, config: Config) -> None:
        self.config: Config = config
        self._playwright: Playwright | None = None
        self._browser: object | None = None
        self._context: object | None = None
        self._page: Page | None = None
        self._diretorio_downloads: Path | None = None

    @property
    def _frame_def(self) -> FrameLocator:
        """Retorna o FrameLocator do frame principal 'frameDef'."""
        return self._page.frame_locator("frame[name=\"frameDef\"]")

    @property
    def _menu_frame(self) -> FrameLocator:
        """Retorna o FrameLocator do menu (dentro de frameDef)."""
        return self._frame_def.frame_locator("#menu")

    @property
    def _content_frame(self) -> FrameLocator:
        """Retorna o FrameLocator do conteudo (dentro de frameDef)."""
        return self._frame_def.frame_locator("#basefrm")

    async def iniciar(self) -> None:
        """Inicializa o Playwright, abre navegador e faz login."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=False)
        self._context = await self._browser.new_context(accept_downloads=True)
        self._page = await self._context.new_page()
        self._page.set_default_timeout(TIMEOUT_PADRAO)

        await self._login()

    async def _login(self) -> None:
        """Acessa o portal e realiza o login."""
        logger.info("Acessando portal de login...")
        await self._page.goto(URL_LOGIN, wait_until="networkidle")

        # Preenche usuario
        await self._page.get_by_role(
            "textbox", name="Digite seu usuário para"
        ).fill(self.config.usuario)

        # Preenche senha
        await self._page.get_by_role(
            "textbox", name="Digite sua senha para acessar"
        ).fill(self.config.senha)

        # Clica em Entrar
        await self._page.get_by_role("link", name="Entrar", exact=True).click()
        await self._page.wait_for_timeout(3000)

        # Tratamento: sessao ativa - abre popup e clica em Entrar novamente
        try:
            link_entrar = self._page.get_by_role("link", name="Entrar", exact=True)
            if await link_entrar.is_visible(timeout=5000):
                logger.info("Outra sessao ativa. Clicando em Entrar novamente...")
                async with self._page.expect_popup() as popup_info:
                    await link_entrar.click()
                popup = await popup_info.value
                await popup.close()
                await self._page.wait_for_timeout(2000)
        except Exception:
            pass

        logger.info("Login realizado")

    async def navegar_para_nota_fiscal(self) -> None:
        """Expande NFS-e Contribuinte e clica em Nota Fiscal."""
        logger.info("Navegando para Nota Fiscal...")

        await self._menu_frame.get_by_role(
            "link", name="NFS-e Contribuinte"
        ).click()
        await self._page.wait_for_timeout(2000)

        await self._menu_frame.get_by_role(
            "link", name="Nota Fiscal"
        ).click()
        await self._page.wait_for_timeout(3000)

    async def executar_consulta(self) -> None:
        """Executa consulta completa para o mes/ano informado."""
        self._diretorio_downloads = criar_diretorio_downloads(
            self.config.ano, self.config.mes,
        )

        for dt_inicio, dt_fim in split_date_range(self.config.ano, self.config.mes):
            logger.info("Consultando periodo %s a %s", dt_inicio, dt_fim)
            await self._preencher_consulta(dt_inicio, dt_fim)
            await self._processar_tabela()

    async def _preencher_consulta(self, data_inicio: str, data_fim: str) -> None:
        """Preenche os campos de data e clica em Consultar."""
        await self._page.wait_for_timeout(1000)

        for campo_id, valor in [("dtFatoGeradorInicial", data_inicio), ("dtFatoGeradorFinal", data_fim)]:
            campo = self._content_frame.locator(f"#{campo_id}")
            await campo.click()
            await campo.fill(valor)
            # Fecha popup de calendario se abriu
            await self._fechar_popups()

        await self._page.wait_for_timeout(500)

        await self._content_frame.get_by_role(
            "link", name="Consultar"
        ).click()

        await self._fechar_popups()

        # Aguarda aparecer uma linha com checkbox (tabela de dados carregada)
        try:
            await self._content_frame.locator(
                "tr:has(input[type='checkbox'])"
            ).first.wait_for(state="visible", timeout=TIMEOUT_CONSULTA)
        except Exception:
            logger.warning("Tabela de resultados nao apareceu a tempo")

    async def _fechar_popups(self) -> None:
        """Fecha janelas popup que nao sejam a pagina principal."""
        try:
            for popup in self._page.context.pages:
                if popup != self._page:
                    await popup.close()
        except Exception:
            pass

    async def _processar_tabela(self) -> None:
        """Percorre todas as paginas e baixa cada NF. Se todas ja foram
        baixadas em alguma pagina, encerra o periodo (evita loop)."""
        pagina = 1

        while True:
            logger.info("Pagina %d", pagina)

            try:
                await self._content_frame.locator(
                    "tr:has(input[type='checkbox'])"
                ).first.wait_for(state="visible", timeout=TIMEOUT_PADRAO)
            except Exception:
                logger.warning("Nenhuma nota encontrada nesta pagina")
                break

            novas = await self._processar_linhas()

            if novas == 0:
                logger.info(
                    "Todas as NFs desta pagina ja foram baixadas. "
                    "Fim do periodo."
                )
                break

            if not await self._ir_proxima_pagina():
                logger.info("Fim das paginas")
                break

            pagina += 1
            await self._page.wait_for_timeout(2000)

    async def _processar_linhas(self) -> int:
        """Itera sobre as linhas da tabela e retorna quantas foram baixadas."""
        linhas = self._content_frame.locator("tr:has(input[type='checkbox'])")
        qtd = await linhas.count()
        novas = 0

        for idx in range(qtd):
            try:
                if await self._processar_linha(linhas.nth(idx)):
                    novas += 1
            except Exception as e:
                logger.error("Erro na linha %d: %s", idx, e)
                await self._capturar_screenshot(f"erro_linha_{idx}")

        return novas

    async def _processar_linha(self, linha: Locator) -> bool:
        """Processa uma linha. Retorna True se baixou uma NF nova."""
        texto = await linha.text_content()
        if not texto:
            return False

        partes = texto.strip().split()
        numero_nf = partes[0] if partes else ""

        if not numero_nf.isdigit():
            return False

        if xml_ja_existe(self._diretorio_downloads, numero_nf):
            return False

        logger.info("Baixando NF %s", numero_nf)

        checkbox = linha.get_by_role("checkbox")
        await checkbox.check()
        await self._page.wait_for_timeout(1500)

        btn_exportar = self._content_frame.locator("#btnInf_Exportar")

        try:
            async with self._page.expect_download(timeout=TIMEOUT_CONSULTA) as download_info:
                await btn_exportar.scroll_into_view_if_needed()
                await self._page.wait_for_timeout(500)
                await btn_exportar.click()

            download: Download = await download_info.value
            resultado = await processar_download(download, self._diretorio_downloads)

            if resultado is not None:
                return True

            logger.error("Falha ao baixar NF %s", numero_nf)
            await self._capturar_screenshot(f"falha_download_{numero_nf}")

        except Exception as e:
            logger.error("Download falhou para NF %s: %s", numero_nf, e)
            await self._capturar_screenshot(f"erro_download_{numero_nf}")

            # Retry com clique forcado
            try:
                await self._page.wait_for_timeout(2000)
                async with self._page.expect_download(timeout=TIMEOUT_CONSULTA) as retry:
                    await btn_exportar.click(force=True, timeout=15000)
                download2 = await retry.value
                await processar_download(download2, self._diretorio_downloads)
            except Exception:
                pass

        finally:
            await checkbox.uncheck()
            await self._page.wait_for_timeout(500)

        return False

    async def _ir_proxima_pagina(self) -> bool:
        """Tenta ir para a proxima pagina da tabela."""
        await self._page.wait_for_timeout(2000)

        try:
            # Le o texto de informacao da paginacao: "Pagina X de Y"
            info = await self._content_frame.locator(
                "#paginacao td:first-child"
            ).text_content(timeout=5000)
            logger.info("Paginacao: %s", info.strip())

            # Tenta extrair "Pagina X de Y" -> pagina_atual e total
            import re
            match = re.search(r"(\d+)\s*de\s*(\d+)", info)
            if match:
                pagina_atual = int(match.group(1))
                total_paginas = int(match.group(2))
                if pagina_atual >= total_paginas:
                    logger.info("Ultima pagina (%d/%d)", pagina_atual, total_paginas)
                    return False

        except Exception:
            pass

        # Tenta clicar no link "Proxima" (a:nth-child(5) conforme codegen)
        try:
            link = self._content_frame.locator("a:nth-child(5)")
            if await link.is_visible(timeout=2000) and await link.is_enabled():
                # Verifica se é realmente "proxima" e nao um numero de pagina
                texto = (await link.text_content() or "").strip()
                if not texto.isdigit():
                    await link.click()
                    logger.info("Clicou em a:nth-child(5) para proxima pagina")
                    await self._page.wait_for_timeout(3000)
                    return True
        except Exception:
            pass

        # Fallback: ultimo <a> dentro da #paginacao
        try:
            ultimo = self._content_frame.locator("#paginacao a").last
            if await ultimo.is_visible(timeout=2000) and await ultimo.is_enabled():
                await ultimo.click()
                logger.info("Clicou no ultimo link da paginacao")
                await self._page.wait_for_timeout(3000)
                return True
        except Exception:
            pass

        logger.info("Nenhum botao de proxima pagina encontrado")
        return False

    async def _capturar_screenshot(self, nome: str) -> None:
        """Salva um screenshot da pagina atual para debug."""
        try:
            pasta_logs = Path(__file__).resolve().parent / "logs"
            pasta_logs.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = pasta_logs / f"{nome}_{ts}.png"
            await self._page.screenshot(path=str(caminho), full_page=True)
            logger.info("Screenshot salvo: %s", caminho)
        except Exception as e:
            logger.warning("Erro ao capturar screenshot: %s", e)

    async def fechar(self) -> None:
        """Fecha navegador e libera recursos."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Navegador fechado")

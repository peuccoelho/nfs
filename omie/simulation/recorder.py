"""Registrador da simulacao: captura cada etapa e gera o relatorio de seletores.

O ``SimulationRecorder`` e injetado como observador opcional na automacao.
Em cada ponto de captura ele salva screenshot + HTML da pagina, registra os
elementos interativos reais e valida os seletores atuais da automacao.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page

from omie.automation.selectors import login as login_selectors
from omie.automation.selectors import navigation as nav_selectors
from omie.automation.selectors import os as os_selectors
from omie.config.settings import Settings
from omie.services.logger import get_logger
from omie.simulation.inspector import (
    inspect_interactive,
    validate_selectors,
)

logger = get_logger(__name__)


class SimulationRecorder:
    """Observer opcional que registra o fluxo durante a automacao.

    Interface minima usada pela automacao:
        ``await recorder.capture(nome, page)``
    """

    def __init__(self, settings: Settings, base_dir: Path) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._root = base_dir / stamp
        self._shots = self._root / "screenshots"
        self._pages = self._root / "paginas"
        self._settings = settings
        self._steps: list[dict[str, Any]] = []
        self._elements: list[dict[str, Any]] = []
        self._validation: list[dict[str, Any]] = []
        self._shots.mkdir(parents=True, exist_ok=True)
        self._pages.mkdir(parents=True, exist_ok=True)
        logger.info("Simulacao registrada em: %s", self._root)

    @property
    def root(self) -> Path:
        return self._root

    async def capture(self, nome: str, page: Page) -> None:
        """Captura o estado atual da pagina como uma etapa da simulacao."""
        indice = len(self._steps) + 1
        prefixo = f"{indice:02d}_{nome}"

        try:
            url = page.url
            titulo = await page.title()
        except Exception:
            url, titulo = "", ""

        screenshot = self._shots / f"{prefixo}.png"
        html = self._pages / f"{prefixo}.html"

        try:
            await page.screenshot(path=str(screenshot), full_page=True)
        except Exception as exc:
            logger.warning("Falha ao capturar screenshot '%s': %s", nome, exc)
            screenshot = None

        try:
            content = await page.content()
            html.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.warning("Falha ao salvar HTML '%s': %s", nome, exc)
            html = None

        elementos = await inspect_interactive(page)
        validacao = await self._validate_for(nome, page)

        self._steps.append(
            {
                "indice": indice,
                "nome": nome,
                "url": url,
                "titulo": titulo,
                "screenshot": str(screenshot) if screenshot else None,
                "html": str(html) if html else None,
                "elementos": len(elementos),
                "validacao": validacao,
            }
        )
        self._elements.append({"etapa": nome, "elementos": elementos})
        for item in validacao:
            self._validation.append({"etapa": nome, **item})

        logger.info(
            "Etapa %02d '%s': URL=%s (screenshot=%s, html=%s)",
            indice,
            nome,
            url,
            bool(screenshot),
            bool(html),
        )

    async def _validate_for(
        self, nome: str, page: Page
    ) -> list[dict[str, Any]]:
        """Valida os seletores atuais relevantes a etapa contra a tela."""
        expected = self._build_expected(nome, page)
        if not expected:
            return []
        return await validate_selectors(page, expected)

    def _build_expected(
        self, nome: str, page: Page
    ) -> list[tuple[str, Locator]]:
        nome_l = nome.lower()

        if "login" in nome_l:
            s = login_selectors
            return [
                ("email_input", s.email_input(page)),
                ("password_input", s.password_input(page)),
                ("submit_button", s.submit_button(page)),
                ("two_factor_input", s.two_factor_input(page)),
                ("app_home_marker", s.app_home_marker(page)),
            ]

        if "empresa" in nome_l:
            s = nav_selectors
            empresa = self._settings.empresa
            return [
                ("company_card", s.company_card(page, empresa)),
                ("access_button",
                 s.access_button_for_company(page, empresa)),
            ]

        if "nfse" in nome_l:
            s = nav_selectors
            return [
                ("menu_servicos", s.servicos_menu_link(page)),
                ("os_list_link", s.os_list_link(page)),
                ("onboarding_later", s.onboarding_later_button(page)),
            ]

        if "os_" in nome_l or "faturad" in nome_l or "dry_run" in nome_l:
            s = os_selectors
            return [
                ("celulas_aguardando", s.aguardando_cells(page)),
                ("faturar_agora", s.faturar_agora(page)),
                ("confirmar_sim", s.confirm_sim(page)),
            ]

        if "sefaz" in nome_l:
            s = os_selectors
            return [
                ("error_link", s.error_required_link(page)),
                ("pesquisar_sefaz", s.pesquisar_sefaz_link(page)),
                ("pesquisar", s.pesquisar_button(page)),
                ("atualizar", s.atualizar_button(page)),
                ("salvar", s.salvar_link(page)),
                ("fechar", s.sefaz_close(page)),
                ("tentar_novamente", s.tentar_novamente(page)),
            ]

        return []

    def finish(self) -> Path:
        """Gera os arquivos finais (fluxo, relatorio de seletores) e retorna a raiz."""
        self._write_fluxo()
        self._write_relatorio()
        self._write_json()
        return self._root

    def _write_fluxo(self) -> None:
        linhas = [
            "# Simulacao do fluxo Omie",
            "",
            f"- Inicio: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"- Empresa: {self._settings.empresa}",
            "",
            "## Etapas",
            "",
        ]
        for etapa in self._steps:
            linhas.append(f"### {etapa['indice']:02d} - {etapa['nome']}")
            linhas.append(f"- URL: {etapa['url']}")
            linhas.append(f"- Título: {etapa['titulo']}")
            linhas.append(f"- Screenshot: `{etapa['screenshot'] or '-'}`")
            linhas.append(f"- HTML: `{etapa['html'] or '-'}`")
            if etapa.get("validacao"):
                linhas.append("- Seletores atuais:")
                for item in etapa["validacao"]:
                    qtd = f" (qtd={item['qtd']})" if item.get("qtd") else ""
                    linhas.append(
                        f"  - {item['seletor_atual']}: **{item['status']}**{qtd}"
                    )
            linhas.append("")
        (self._root / "fluxo.md").write_text("\n".join(linhas), encoding="utf-8")

    def _write_relatorio(self) -> None:
        linhas = [
            "# Relatorio de seletores - Omie",
            "",
            "Cada elemento abaixo foi encontrado na tela real. Use os seletores"
            " sugeridos para corrigir os modulos em `omie/automation/selectors/`.",
            "",
        ]
        for bloco in self._elements:
            linhas.append(f"## Etapa: {bloco['etapa']}")
            for el in bloco["elementos"]:
                sel = el.get("seletores") or {}
                desc = f"- `{el['tag']}`"
                if el.get("id"):
                    desc += f" `#{el['id']}`"
                if el.get("text"):
                    desc += f' texto="{el["text"]}"'
                desc += " [visivel]" if el.get("visible") else " [oculto]"
                linhas.append(desc)
                if el.get("placeholder"):
                    linhas.append(f"    - placeholder: {el['placeholder']}")
                if el.get("ariaLabel"):
                    linhas.append(f"    - aria-label: {el['ariaLabel']}")
                if el.get("name"):
                    linhas.append(f"    - name: {el['name']}")
                classes = ", ".join(el.get("classes") or []) or "-"
                linhas.append(f"    - class: {classes}")
                linhas.append(f"    - CSS: `{sel.get('css', '-')}`")
                linhas.append(f"    - XPath: `{sel.get('xpath', '-')}`")
            linhas.append("")

        linhas.append("## Validacao dos seletores atuais")
        linhas.append("")
        linhas.append("| Etapa | Seletor | Status |")
        linhas.append("|-------|---------|--------|")
        for item in self._validation:
            linhas.append(
                f"| {item['etapa']} | {item['seletor_atual']} | {item['status']} |"
            )
        (self._root / "seletores.md").write_text("\n".join(linhas), encoding="utf-8")

    def _write_json(self) -> None:
        payload = {
            "steps": self._steps,
            "elements": self._elements,
            "validation": self._validation,
        }
        (self._root / "seletores.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

"""Inspecao do DOM: coleta elementos interativos e sugere seletores.

Usado pelo modo de simulacao/inspecao para registrar as telas reais do Omie e
gerar sugestoes de seletores (CSS/XPath) para corrigir os modulos de
``selectors`` da automacao.
"""
from __future__ import annotations

import re
from typing import Any

from playwright.async_api import Locator, Page

from omie.services.logger import get_logger

logger = get_logger(__name__)

#: Elementos considerados interativos/relevantes para a automacao.
INTERACTIVE_SELECTOR = (
    "input, textarea, select, button, a[href], "
    "[role='button'], [role='link'], [role='tab'], [role='menu'], "
    "[role='menuitem'], [role='checkbox'], [role='radio'], "
    "[draggable='true'], [contenteditable='true']"
)

#: Limite de elementos registrados por captura (evita relatorios gigantes).
MAX_ELEMENTS = 300

#: JS que extrai, de forma otimizada, os atributos de todos os elementos.
_ELEMENTS_JS = """(els) => {
  const out = [];
  for (const el of els) {
    if (el.closest('script, style, noscript, svg')) continue;
    const attrs = {};
    for (const a of el.attributes) attrs[a.name] = a.value;
    const text = (el.innerText || el.textContent || '')
      .replace(/\\s+/g, ' ').trim().slice(0, 120);
    const rects = el.getClientRects();
    let visible = rects.length > 0 && rects[0].width > 0 && rects[0].height > 0;
    if (visible) {
      const style = getComputedStyle(el);
      visible = style.display !== 'none' && style.visibility !== 'hidden';
    }
    const tag = el.tagName.toLowerCase();
    if (!visible && !attrs.id && !attrs.name && !attrs.placeholder
        && !attrs['aria-label'] && attrs.draggable !== 'true' && !text) {
      continue;
    }
    out.push({
      tag,
      id: attrs.id || null,
      name: attrs.name || null,
      type: attrs.type || null,
      placeholder: attrs.placeholder || null,
      ariaLabel: attrs['aria-label'] || attrs.title || null,
      role: attrs.role || null,
      draggable: attrs.draggable || null,
      href: attrs.href || null,
      classes: (attrs.class || '').split(/\\s+/).filter(Boolean).slice(0, 8),
      text,
      visible,
      attrs: Object.fromEntries(
        Object.entries(attrs).filter(([k]) =>
          !['class', 'style', 'id', 'name', 'type', 'placeholder',
            'aria-label', 'title', 'role', 'draggable', 'href'].includes(k)
        )
      ),
    });
  }
  return out;
}"""


def _css_escape(ident: str) -> str:
    """Escapa um valor para uso em seletor CSS (identificador)."""
    return re.sub(r"([^a-zA-Z0-9_-])", r"\\\1", ident)


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_selectors(info: dict[str, Any]) -> dict[str, str]:
    """Gera sugestoes de seletor (CSS e XPath) a partir dos dados do elemento.

    A ordem de preferencia: id > classes > name > placeholder > aria-label >
    texto acessivel.
    """
    tag = info.get("tag") or "div"
    css: list[str] = []
    xpath: list[str] = []

    if info.get("id"):
        css.append(f"#{_css_escape(info['id'])}")
        xpath.append(f"//{tag}[@id='{info['id']}']")

    classes = [c for c in (info.get("classes") or []) if c]
    if classes:
        css.append(f"{tag}.{'.'.join(classes[:3])}")
        xpath.append(
            f"//{tag}[contains(concat(' ',normalize-space(@class),' '),' "
            f"{classes[0]} ')]"
        )

    if info.get("name"):
        css.append(f"{tag}[name='{_quote(info['name'])}']")
        xpath.append(f"//{tag}[@name='{_quote(info['name'])}']")

    if info.get("placeholder"):
        css.append(f"{tag}[placeholder='{_quote(info['placeholder'])}']")
        xpath.append(f"//{tag}[@placeholder='{_quote(info['placeholder'])}']")

    if info.get("ariaLabel"):
        css.append(f"{tag}[aria-label='{_quote(info['ariaLabel'])}']")
        xpath.append(f"//{tag}[@aria-label='{_quote(info['ariaLabel'])}']")

    if info.get("href"):
        css.append(f"{tag}[href*='{_quote(str(info['href'])[:60])}']")

    if info.get("text") and tag in ("button", "a", "input", "h1", "h2", "h3",
                                    "h4", "span", "div", "li"):
        txt = info["text"]
        if len(txt) <= 80:
            xpath.append(f"//{tag}[normalize-space()='{_quote(txt)}']")

    if not css:
        css.append(tag)
    if not xpath:
        xpath.append(f"//{tag}")

    return {"css": css[0], "xpath": xpath[0]}


async def inspect_interactive(page: Page) -> list[dict[str, Any]]:
    """Extrai os elementos interativos relevantes da pagina atual.

    Returns:
        Lista de dicts com atributos reais do elemento e seletores sugeridos.
    """
    try:
        elementos = await page.eval_on_selector_all(
            INTERACTIVE_SELECTOR, _ELEMENTS_JS
        )
    except Exception as exc:
        logger.warning("Falha ao inspecionar o DOM: %s", exc)
        return []

    for el in elementos:
        el["seletores"] = build_selectors(el)

    elementos.sort(
        key=lambda e: (
            0 if e.get("visible") else 1,
            0 if any(e.get(k) for k in ("id", "name", "placeholder",
                                        "ariaLabel", "draggable")) else 1,
        )
    )
    return elementos[:MAX_ELEMENTS]


async def validate_selectors(
    page: Page,
    expected: list[tuple[str, Locator]],
    timeout_ms: int = 1500,
) -> list[dict[str, Any]]:
    """Testa seletores da automacao contra a tela atual.

    Args:
        expected: lista de ``(descricao, locator)`` dos seletores atuais.

    Returns:
        Lista de dicts com o status de cada seletor (ENCONTRADO/NAO
        ENCONTRADO/visivel/oculto/ERRO).
    """
    resultado: list[dict[str, Any]] = []
    for descricao, locator in expected:
        try:
            count = await locator.count()
        except Exception as exc:
            resultado.append(
                {"seletor_atual": descricao, "status": "ERRO", "detalhe": str(exc)}
            )
            continue

        if count == 0:
            resultado.append(
                {"seletor_atual": descricao, "status": "NAO ENCONTRADO", "qtd": 0}
            )
            continue

        visivel = False
        try:
            visivel = await locator.first.is_visible(timeout=timeout_ms)
        except Exception:
            pass

        resultado.append(
            {
                "seletor_atual": descricao,
                "status": "visivel" if visivel else "oculto",
                "qtd": count,
            }
        )
    return resultado

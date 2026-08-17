#! /usr/bin/env python3
"""Abre o Playwright Codegen na empresa PFO Turismo com a sessao ja logada.

O codegen grava os passos (cliques, filtros, texto digitado) em
``logs/codegen_os_list.py`` enquanto voce navega manualmente ate a lista de OS
e faz o passo a passo do faturamento. Depois e so me mostrar o arquivo.

Uso:
    python codegen_pfo.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

URL_PFO = "https://app.omie.com.br/gestao/pfo-cow05sxa/"


def main() -> int:
    base = Path(__file__).resolve().parent
    storage = base / "logs" / "sessao_omie.json"
    saida = base / "logs" / "codegen_os_list.py"
    if not storage.exists():
        print(f"Sessao nao encontrada: {storage}")
        print("Rode primeiro: python simulate_omie.py --no-trace")
        return 1
    saida.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        "--load-storage",
        str(storage),
        "--target",
        "python-async",
        "-o",
        str(saida),
        URL_PFO,
    ]
    print("Codegen aberto em PFO Turismo (sessao ja logada).")
    print(f"Ao fechar, o codigo ficara em: {saida}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())

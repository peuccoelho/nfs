"""Modelos de dados e geracao do relatorio final da execucao."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from omie.services.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkOrderResult:
    """Resultado do processamento de uma ordem de servico."""

    os_id: str
    status: str  # "success" | "failure"
    attempts: int
    duration_seconds: float
    error: str | None = None


@dataclass
class ExecutionResult:
    """Resumo geral de uma execucao."""

    started_at: datetime
    finished_at: datetime | None = None
    step_log: list[str] = field(default_factory=list)
    work_orders: list[WorkOrderResult] = field(default_factory=list)

    @property
    def total_os(self) -> int:
        return len(self.work_orders)

    @property
    def success_count(self) -> int:
        return sum(1 for wo in self.work_orders if wo.status == "success")

    @property
    def failure_count(self) -> int:
        return sum(1 for wo in self.work_orders if wo.status == "failure")

    @property
    def total_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return max(0.0, (self.finished_at - self.started_at).total_seconds())


class ReportGenerator:
    """Gera relatorio Markdown e JSON com o resumo da execucao."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def generate(self, result: ExecutionResult) -> tuple[Path, Path]:
        """Escreve os relatorios em ``output/`` e retorna os caminhos."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        md_path = self._output_dir / f"relatorio_omie_{stamp}.md"
        json_path = self._output_dir / f"relatorio_omie_{stamp}.json"

        md_path.write_text(self._render_markdown(result), encoding="utf-8")
        json_path.write_text(self._render_json(result), encoding="utf-8")

        logger.info("Relatorio gerado: %s e %s", md_path.name, json_path.name)
        return md_path, json_path

    def _render_markdown(self, result: ExecutionResult) -> str:
        linhas = [
            "# Relatorio - Faturamento de Ordens de Servico (Omie)",
            "",
            f"- Inicio: {result.started_at:%Y-%m-%d %H:%M:%S}",
            f"- Fim: {result.finished_at:%Y-%m-%d %H:%M:%S}",
            f"- Tempo total: {result.total_seconds:.1f}s",
            f"- OS processadas: {result.total_os}",
            f"- Sucesso: {result.success_count}",
            f"- Falhas: {result.failure_count}",
            "",
            "## Ordens de servico",
            "",
            "| OS | Status | Tentativas | Tempo (s) | Erro |",
            "|----|--------|-----------:|----------:|------|",
        ]
        for wo in result.work_orders:
            linhas.append(
                f"| {wo.os_id} | {wo.status} | {wo.attempts} | "
                f"{wo.duration_seconds:.1f} | {wo.error or '-'} |"
            )

        if result.step_log:
            linhas.extend(["", "## Etapas executadas"])
            for indice, etapa in enumerate(result.step_log, start=1):
                linhas.append(f"{indice}. {etapa}")

        return "\n".join(linhas) + "\n"

    def _render_json(self, result: ExecutionResult) -> str:
        payload = {
            "inicio": result.started_at.isoformat(),
            "fim": result.finished_at.isoformat() if result.finished_at else None,
            "tempo_total_segundos": round(result.total_seconds, 2),
            "total_os": result.total_os,
            "sucesso": result.success_count,
            "falhas": result.failure_count,
            "etapas": result.step_log,
            "ordens": [asdict(wo) for wo in result.work_orders],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

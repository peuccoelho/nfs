"""Retry automatico para operacoes criticas.

Prefira `retry_async` em operacoes que podem falhar de forma transitoria
(conexao, elementos de interface). Excecoes de negocio nao devem ser
repetidas automaticamente.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from omie.utils.exceptions import RetryExhaustedError

T = TypeVar("T")

Coro = Callable[..., Awaitable[T]]


async def retry_async(
    func: Coro[T],
    *,
    max_attempts: int,
    delay_seconds: float = 2.0,
    backoff_factor: float = 1.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    logger: logging.Logger | None = None,
    description: str = "operacao",
    **kwargs: Any,
) -> T:
    """Executa ``func`` com retry ate obter sucesso ou atingir o limite.

    Args:
        func: corrotina a ser executada.
        max_attempts: numero maximo de tentativas (>= 1).
        delay_seconds: atraso inicial entre tentativas.
        backoff_factor: multiplicador de atraso a cada tentativa.
        exceptions: tupla de excecoes consideradas recuperaveis.
        logger: logger opcional para registrar as tentativas.
        description: nome legivel da operacao (usado nas mensagens).
        **kwargs: argumentos repassados a ``func``.

    Returns:
        Retorno de ``func``.

    Raises:
        RetryExhaustedError: quando todas as tentativas falham.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser >= 1")

    for attempt in range(1, max_attempts + 1):
        try:
            return await func(**kwargs)
        except exceptions as exc:
            if attempt >= max_attempts:
                raise RetryExhaustedError(
                    f"{description} falhou apos {max_attempts} tentativas"
                ) from exc
            wait = delay_seconds * (backoff_factor ** (attempt - 1))
            if logger:
                logger.warning(
                    "Tentativa %d/%d de %s falhou (%s). Repetindo em %.1fs.",
                    attempt,
                    max_attempts,
                    description,
                    exc,
                    wait,
                )
            await asyncio.sleep(wait)

    raise RetryExhaustedError(f"{description} falhou")  # pragma: no cover

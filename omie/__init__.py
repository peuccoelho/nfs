"""Automacao de faturamento de Ordens de Servico no Omie.

Pacote modular dividido em:
    - config:     configuracoes e credenciais
    - automation: etapas da automacao (login, navegacao, kanban, NFS-e, SEFAZ)
    - services:   servicos transversais (logger, autenticacao, relatorio)
    - utils:      utilitarios reutilizaveis (retry, screenshots, excecoes)
"""

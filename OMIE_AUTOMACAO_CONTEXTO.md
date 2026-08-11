# Omie NFS-e — Contexto da Automação

Documento de contexto único para futuras alterações no sistema de automação de
faturamento de Ordens de Serviço (NFS-e) no portal Omie.

---

## 1. Objetivo

Faturar NFS-e em loop até que **não reste nenhuma OS "aguardando faturamento"** na
lista, com:

- Resiliência a rede instável (esperas explícitas, retry/backoff).
- Skip de OS não faturáveis sem quebrar o loop (idempotência e tolerância a erros).
- Reinício seguro: a mesma OS nunca é faturara duas vezes (skip de "já foi faturada").

---

## 2. Pilha e ambiente

| Item                | Valor                                                        |
| ------------------- | ------------------------------------------------------------ |
| Linguagem           | Python 3.12                                                  |
| Automação           | Playwright `1.60.0` (Chromium)                               |
| Config              | `.env` na raiz (`OMIE_EMAIL`, `OMIE_SENHA`)                  |
| Config de código    | `Settings` (dataclass frozen) em `omie/config/settings.py`   |
| Empresas suportadas | `SUPPORTED_EMPRESAS = ("PFO Turismo", "Nucleo")`             |
| Logs                | `logs/omie_automation_YYYYMMDD_HHMMSS.log`                   |
| Sessão persistida   | `logs/sessao_omie.json` (storage_state do Playwright)        |
| Artefatos           | `logs/simulacao/<timestamp>/` (screenshots, HTML, seletores) |
| Relatório           | `output/relatorio_omie_<stamp>.md` + `.json`                 |

---

## 3. Estrutura do projeto e responsabilidades

```
nfs/
├── simulate_omie.py          # CLI principal (argparse: --full, --no-trace, --empresa)
├── main_omie.py              # Ponto de entrada CLI (runner + relatório)
├── main.py, gui.py, config.py, downloader.py, utils.py, portal.py
│                             # app root (GUI/legado — fora do loop atual usado)
├── gui_omie.py               # GUI alternativa (não usada no loop atual)
├── omie/
│   ├── config/
│   │   ├── settings.py       # Settings frozen, SUPPORTED_EMPRESAS, project_root()
│   │   └── credentials.py    # Credentials (e-mail/senha) lidas do .env
│   ├── automation/
│   │   ├── browser.py        # BrowserManager: Chromium, storage_state, tracing
│   │   ├── login.py          # LoginFlow resiliente + sessão persistida
│   │   ├── navigation.py     # seleção empresa, onboarding/popups, ir para lista
│   │   ├── faturamento.py    # OSService: loop de faturamento, condicionais, SEFAZ, skip
│   │   ├── sefaz.py          # correção de dados no SEFAZ (campos obrigatórios)
│   │   ├── runner.py         # AutomationRunner: retry, aplicação de empresa (_apply_empresa)
│   │   ├── waits.py          # Waits: settle() e click() resilientes, esperas explícitas
│   │   └── dialogs.py        # Tkinter: ask_2fa_code e ask_empresa (thread separada)
│   ├── automation/selectors/
│   │   ├── common.py         # seletores genéricos (dialogs, botões comuns)
│   │   ├── login.py          # seletores da tela de login
│   │   ├── navigation.py     # seletores de menu/empresa/onboarding/popups
│   │   ├── os.py             # seletores da lista/célula/checklist de OS
│   │   └── sefaz.py          # seletores do portal SEFAZ
│   ├── services/
│   │   ├── logger.py         # setup_logging + get_logger (console + arquivo)
│   │   ├── report.py         # WorkOrderResult, ExecutionResult, ReportGenerator (MD+JSON)
│   │   └── authentication.py # autenticação (2FA etc.)
│   ├── simulation/
│   │   └── recorder.py       # SimulationRecorder: screenshots/HTML/seletores
│   └── utils/
│       ├── retry.py          # decorators/helpers de retry
│       ├── screenshots.py    # captura de screenshots
│       └── exceptions.py     # ElementNotFoundError, CredentialsError, etc.
└── requirements.txt, .env, .gitignore
```

### Papéis-chave no loop atual

- `simulate_omie.py` — entrada CLI; `--full` (loop completo), `--no-trace` (desliga tracing), `--empresa <nome>`.
- `AutomationRunner.run()` (`omie/automation/runner.py`) — orquestra login → empresa → loop de OS → relatório.
- `OSService` (`omie/automation/faturamento.py`) — processa cada OS: condicionais, SEFAZ ou skip.
- `Waits.settle()` / `Waits.click()` (`omie/automation/waits.py`) — aguarda rede assentar e clica com retry/backoff para erros transitórios.
- `BrowserManager` (`omie/automation/browser.py`) — abre/fecha Chromium, salva e reusa `storage_state`.

---

## 4. Fluxo real validado (empresa Nucleo)

Sequência confirmada nas rodadas recentes:

1. **Login** no portal Omie → botão **"Acessar"** abre a conta em nova aba.
2. Onboarding: **"Depois"** (dispensa onboarding).
3. **Popup "Primeiros Passos"** (conta Nucleo) — fecha com botão **"Fechar"**.
4. Menu **"Serviços e NFS-e"** → **"Listar todas as"** (lista de OS).
5. Para cada OS:
   - Célula com status **"Aguardando faturamento"** → botão **"Faturar Agora"**.
   - Confirmação **"Sim"**.
   - Abre o checklist **"Conferindo a Ordem de Serviço"**:
     - Sem erros → botão **"OK"** (fatura).
     - **Condicional "Alguns campos obrigatórios"** → fluxo SEFAZ (ver abaixo).
     - Qualquer outro erro → **fechar UMA vez** e **pular** a OS.
6. Retorna à lista e segue para a próxima OS até não sobrar "aguardando faturamento".

### Fluxo SEFAZ (somente campos obrigatórios)

`Pesquisar` → `Pesquisar` → `Atualizar` → `Salvar` → `Fechar` → `Tentar Novamente`
(corrige os dados no portal SEFAZ antes de retomar o faturamento).

---

## 5. Regras críticas de automação

- **Front dialog:** cada passo de dialog abre um `div [id^='dialog-outer-wrapper-']`
  (front dialog, último no DOM). **Ações devem ser escopadas a esse div**.
- **Empresa:** com `--empresa` informado, o runner aplica via `_apply_empresa`;
  sem flag, abre Tkinter `ask_empresa` (radio: PFO Turismo / Nucleo).
- **Idempotência:** OS já faturada é pulada (skip) — reinício seguro sem duplicar.
- **Texto de erro quebrado em tags:** usar `a:has-text(...)` (não `text=`),
  padrão gerado pelo Playwright Codegen.
- **União de condicionais:** o conjunto de erros deve ser **CSS-only**
  (`:has-text`). Não misturar engine `text=` com `:has-text` na mesma união
  (causa erro de format).
- **Detecção de erros com espera única** (union) em vez de checagens sequenciais curtas.
- **`TargetClosedError`:** importado de `playwright._impl._errors` e **relançado**
  de `process_all` (não engolido).
- **Skip por erro:** após erro detectado, fechar **UMA vez** o dialog para voltar à
  tabela e pular a OS. Fechar **duas vezes** cai de volta no menu (comportamento indesejado).

---

## 6. Histórico de bugs/armadilhas resolvidas

| Problema                                  | Causa                                                             | Solução                                                                |
| ----------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Popup "Primeiros Passos" atrapalhava      | Aparece APÓS entrar no módulo                                     | Fechar com botão "Fechar" antes de "Listar todas as"                   |
| Checklist "Conferindo a Ordem de Serviço" | Exige botão "OK" para faturar                                     | Aguardar OK quando não há erro                                         |
| Skip errado caía no menu                  | Fechar o dialog 2 vezes                                           | Fechar UMA vez e pular                                                 |
| "falta preencher o X" de endereço         | Texto vizinho ao do SEFAZ ("...preencher o Bairro...")            | MANTIDO: OS é pulada (decisão do usuário)                              |
| "confirmacao 'Sim' nao ficou visivel"     | Overlay/notificação intercepta "Faturar Agora" ou o dialog demora | `_open_billing` re-tenta Faturar Agora→Sim até 3x dispensando overlays |
| Erro ao usar `text=`                      | Texto quebrado em várias tags                                     | Usar `a:has-text(...)`                                                 |
| Erro de format na união de seletores      | Mistura de engine `text=` + CSS                                   | União CSS-only com `:has-text`                                         |
| Erros transitórios (rede/overlay/stale)   | Interceptação, rede instável                                      | `Waits.settle()` + `Waits.click()` com retry/backoff                   |

---

## 7. Empresas e configuração

- `Settings` (frozen dataclass) centraliza timeouts, diretórios, headless e `SUPPORTED_EMPRESAS`.
- Credenciais somente no `.env` (`OMIE_EMAIL`, `OMIE_SENHA`); nunca commit de valores.
- Seleção de empresa: flag `--empresa <nome>` ou Tkinter `ask_empresa`.

---

## 8. Sessão, artefatos e execução

- **Sessão:** após o primeiro login válido, o `storage_state` é salvo em
  `logs/sessao_omie.json`; nas próximas execuções a sessão é reutilizada
  (**sem 2FA repetido**).
- **Artefatos:** cada rodada com tracing grava em `logs/simulacao/<timestamp>/`
  (screenshots, HTML, seletores). Histórico incompleto também em `logs/`.
- **Relatório:** `output/relatorio_omie_<stamp>.md` e `.json` com resumo por OS
  (status: `success` | `via_sefaz` | `simulada` | `pulada` | `failure`).

### Comandos

```bash
# Loop completo na empresa Nucleo, sem tracing
python simulate_omie.py --full --no-trace --empresa Nucleo

# Com tracing (gera artefatos de simulação)
python simulate_omie.py --full --empresa Nucleo
```

---

## 9. Pendências / próximos passos

- **`_extract_os_id` (resolvido):** passou a ler a coluna "Número" da grade
  (`os_selectors.os_number_cell` localiza pela header `th[id$='_NUMERO']`) em
  vez do texto completo da linha, evitando capturar o valor em R$ ou outros
  números. O regex na linha inteira permanece apenas como fallback.
- **Legados removidos:** `omie/automation/invoice.py`, `omie/automation/kanban.py`
  e `omie/automation/selectors/kanban.py` (fluxo kanban/invoice) foram **excluídos**
  — não faziam parte do loop atual de faturamento.
- **`downloader.py` / GUI root:** app root possui utilitários (downloader, portal)
  não usados pelo loop atual — revisar pertinência.

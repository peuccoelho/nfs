# Omie NFS-e — Contexto da Automação

Documento de contexto único da automação de faturamento de Ordens de Serviço
(NFS-e) no portal Omie. Fonte da verdade para retomar o trabalho remoto com o
opencode sem depender do histórico de sessão.

---

## 1. Objetivo

Faturar NFS-e em loop até que **não reste nenhuma OS "aguardando faturamento"**
na lista, com:

- **Resiliência a rede instável** — esperas explícitas, retry/backoff.
- **Skip de OS não faturáveis** sem quebrar o loop (idempotência/tolerância).
- **Reinício seguro** — a mesma OS nunca é faturada duas vezes (skip de
  "já foi faturada").

---

## 2. Pilha e ambiente

| Item                | Valor                                                                 |
| ------------------- | --------------------------------------------------------------------- |
| Linguagem           | Python 3.12                                                           |
| Automação           | Playwright `>=1.40` (async API, Chromium)                             |
| Config              | `.env` na raiz (`OMIE_EMAIL`, `OMIE_SENHA`, `OMIE_EMPRESA`, ...)      |
| Config de código    | `Settings` (dataclass frozen) em `omie/config/settings.py`            |
| Empresas suportadas | `SUPPORTED_EMPRESAS = ("PFO Turismo", "Nucleo")` em `settings.py`     |
| Logs                | `logs/omie_automation_YYYYMMDD_HHMMSS.log`                            |
| Sessão persistida   | `logs/sessao_omie.json` (storage_state do Playwright)                 |
| Artefatos inspeção  | `logs/simulacao/<timestamp>/` (screenshots, HTML, trace, seletores)   |
| Relatório           | `output/relatorio_omie_<stamp>.md` + `.json`                          |
| Empacotamento       | `build_omie.bat` (PyInstaller, onefile/windowed) → `dist/Omie_NFSe_Automation.exe` |

### Chaves `.env` (ver `.env.example`)

- `OMIE_EMAIL`, `OMIE_SENHA` — credenciais obrigatórias.
- `OMIE_EMPRESA` — padrão `PFO Turismo` (sobrescrito por `--empresa`/GUI).
- `OMIE_URL` — padrão `https://app.omie.com.br/`.
- `OMIE_TIMEOUT_MS` (30000), `OMIE_RESULT_WAIT_MS` (15000),
  `OMIE_RETRIES_MAX` (3), `OMIE_RETRY_DELAY_S` (2.0).
- `OMIE_HEADLESS` — `false` (janela visível) por padrão.

---

## 3. Ponto de entrada (o que rodar)

- **`simulate_omie.py`** — CLI principal de uso diário. Sem `--full` roda
  **dry-run** (inspeciona, não fatura); `--full` executa o faturamento real.
  Cria `SimulationRecorder`, liga tracing (exceto `--no-trace`) e passa
  `dry_run`, `session_path` e `empresa` ao runner. Argumentos: `--full`,
  `--no-trace`, `--empresa <nome>` (choices = `SUPPORTED_EMPRESAS`).
- **`main_omie.py`** — CLI enxuta (sem recorder/dry-run): roda e gera o
  relatório via `ReportGenerator`.
- **`gui_omie.py`** — GUI Tkinter (`OmeGui`) usada no `.exe` empacotado:
  escolha de empresa, modo real/simulação, execução em thread, log ao vivo,
  botões para abrir `.env`, `logs/`, `output/`. Roda `AutomationRunner` com
  `dry_run=modo=="simulacao"` e `empresa` fixa (sem prompt Tkinter).

---

## 4. Estrutura do projeto e responsabilidades

```
nfs/
├── simulate_omie.py          # CLI principal (--full, --no-trace, --empresa)
├── main_omie.py              # CLI enxuta: runner + relatório
├── gui_omie.py               # GUI Tkinter (usada no .exe)
├── build_omie.bat            # build PyInstaller → .exe
├── OMIE_AUTOMACAO_CONTEXTO.md# ESTE documento
├── main.py / gui.py / config.py / downloader.py / portal.py / utils.py
│                             # app root legado (outro projeto / fora do loop)
├── omie/
│   ├── config/
│   │   ├── settings.py       # Settings frozen; SUPPORTED_EMPRESAS; project_root()
│   │   └── credentials.py    # Credentials (e-mail/senha) validadas do .env
│   ├── automation/
│   │   ├── browser.py        # BrowserManager: Chromium, context, storage_state, tracing
│   │   ├── login.py          # LoginFlow: login resiliente + táctica sessão ativa
│   │   ├── navigation.py     # Navigation: empresa, onboarding/Depois, Primeiros Passos, lista
│   │   ├── faturamento.py    # OSService: LOOP de faturamento + SEFAZ inline (núcleo)
│   │   ├── waits.py          # Waits: settle()/click() resilientes, visible/hidden/attached
│   │   ├── dialogs.py        # Tkinter ask_2fa_code / ask_empresa (thread separada)
│   │   ├── runner.py         # AutomationRunner: retry global, empresa, troca para aba do app
│   │   └── sefaz.py          # SefazUpdater: NÃO USADO no loop atual (alternativa não ligada)
│   ├── automation/selectors/
│   │   ├── common.py         # helpers genéricos get_by_role/text/placeholder
│   │   ├── login.py          # seletores do login (email/senha/2FA)
│   │   ├── navigation.py     # empresa 'Acessar', menu, "Listar todas as", front_dialog
│   │   ├── os.py             # OS: células, filtro, Faturar Agora, condicionais, SEFAZ
│   │   └── sefaz.py          # seletores SEFAZ (utilizados só via SefazUpdater OUT)
│   ├── services/
│   │   ├── logger.py         # setup_logging + get_logger (console + arquivo)
│   │   ├── report.py         # WorkOrderResult, ExecutionResult, ReportGenerator
│   │   └── authentication.py # AuthenticationService: 2FA (digita, Enter, botão)
│   ├── simulation/
│   │   ├── recorder.py       # SimulationRecorder: observer de capture() nas etapas
│   │   └── inspector.py      # inspeção do DOM real + sugere/valida seletores
│   └── utils/
│       ├── exceptions.py     # hierarquia AutomationError (Config/Credentials/Login/...)
│       ├── retry.py          # retry_async com backoff (RetryExhaustedError)
│       └── screenshots.py    # screenshot/HTML em erro (capture_error_snapshot)
├── requirements.txt          # playwright>=1.40.0, python-dotenv>=1.0.0
└── .env / .env.example / .gitignore
```

### Papéis-chave no loop atual

- `simulate_omie.py` → `AutomationRunner.run()` → orquestra login → empresa →
  aba do app → módulo NFS-e → `OSService.process_all()` → relatório.
- `OSService` (`faturamento.py`) — núcleo: loop, filtro de situação, `_bill_one`,
  detecção de condicionais via união CSS-only, correção SEFAZ **inline**
  (`_sefaz_correction`), skip.
- `Waits.settle()` / `Waits.click()` — aguarda a rede assentar (conta recursos de
  `performance`) e clica com retry/backoff.
- `Waits.visible/hidden/attached` — esperas explícitas; `click` levanta
  `ElementNotFoundError` ao esgotar.
- `BrowserManager` — abre/fecha Chromium; salva e reusa `storage_state`.
- `SimulationRecorder` / `inspector.py` — capturam screenshots/HTML, listam
  elementos interativos reais e validam os seletores atuais em cada etapa.

---

## 5. Fluxo real validado (empresa Nucleo)

1. **Login** no portal Omie → botão **"Acessar"** abre a conta em nova aba.
   - Se houver sessão persistida (`logs/sessao_omie.json`), pula o login.
   - Fluxo de credenciais: e-mail → (opcional) botão **"Continuar"** → senha →
     **"Entrar"** → 2FA (**janela Tkinter** solicita o código).
2. Seleção de empresa: flag `--empresa`/GUI **ou** janela Tkinter `ask_empresa`.
3. Portal de apps → `select_company()` → **"Acessar"** do cartão.
4. `_switch_to_app_page()` — localiza a aba do app (`app.omie.com.br` /
   `hype.omie.com.br`, sem "login"/"meus-aplicativos") e re-aponta a página.
5. `dismiss_onboarding()` — fecha tour com **"Depois"** (logo após o app abrir).
6. Menu **"Serviços e NFS-e"** → `dismiss_onboarding` + `dismiss_primeiros_passos`
   (popup **"Primeiros Passos"** só na conta Nucleo, fecha com **"Fechar"**) →
   link **"Listar todas as"**.
7. `OSService.process_all()`:
   - 1ª iteração: `_apply_aguardando_filter()` — preenche o filtro da coluna
     "Situação" (`td.ui-iggrid-filtercell.SITUACAO input...`) com `aguardando` +
     Enter, se ainda não estiver filtrado. Idempotente.
   - Próximas iterações: `_refresh_list()` (lista visível se "pulada"; senão
     reabre o menu → "Listar todas as").
- Célula com status **"Aguardando faturamento"** → `_open_billing()`:
      clique na **célula do cliente** (coluna `NOME_CLI`; a célula de status
      NÃO abre o detalhe) → **"Faturar Agora"** → **"Sim"** (até 3x,
      dispensando overlays entre tentativas).
   - Após "Sim": `_detect_error_kind()` espera UMA vez por qualquer erro
     (union CSS-only) e classifica:
     - `None` → clicar **"OK"** do checklist **"Conferindo a Ordem de Serviço"**
       → sucesso. Se um erro surgir após o OK, trata recursivamente.
     - `fields` → **correção SEFAZ** (ver abaixo).
     - `item` / `nbs` / `already` / `unknown` → fechar o dialog **UMA vez** e
       **pular** a OS.
8. Repete até não restar OS "aguardando faturamento".

### Fluxo SEFAZ (somente `fields` — "Alguns campos obrigatórios")

Sequência (Codegen): link do erro → `Pesquisar SEFAZ` → `Pesquisar` →
`Atualizar as informações` → `Salvar` → `Fechar` → `Tentar Novamente`.

- O link **`Salvar`** está na **barra de ferramentas** do diálogo
  (`#dialogToolbar-50113`), NÃO no corpo `#dialog-50113`. Seletor
  `salvar_link` escopa `[id^='dialogToolbar-']`.
- O **`Fechar`** do diálogo SEFAZ está no corpo `#dialog-50113`.

- Se, após o SEFAZ, ainda vier **item específico** (`ERROR_ITEM_FRAGMENT`) ou
  **Código NBS** (`ERROR_NBS_FRAGMENT`) ou **campos obrigatórios** de novo →
  a OS é **pulada** (preenchimento manual depois). Status final `pulada`.
- Caso contrário, o billing é aceito → status `via_sefaz`.

> Atenção: a correção SEFAZ que roda é a **inline** `OSService._sefaz_correction()`
> em `faturamento.py`, usando os seletores de `selectors/os.py`
> (front_dialog). O módulo `automation/sefaz.py` (`SefazUpdater`, com
> `SefazUpdater.fix_and_return()`) e `selectors/sefaz.py` **não estão ligados ao
> loop** — são uma implementação alternativa/legada. Se forem usados, revisar.

---

## 6. Regras críticas de automação

- **Front dialog:** cada dialog abre `div [id^='dialog-outer-wrapper-']`
  (última visível no DOM). **Ações devem ser escopadas a esse div**
  (`selectors/os.front_dialog`) para não clicar em telas de fundo.
- **Empresa:** `--empresa` na CLI ou radio na GUI → `_apply_empresa()` via
  `dataclasses.replace`; sem flag → Tkinter `ask_empresa`.
- **ID da OS na grade:** a grade da PFO **não tem coluna `Número`**. O id está
  em `tr[data-id="..."]` (`os_row_id`). `_extract_os_id` lê `data-id` primeiro,
  depois a coluna `Número` (header `th[id$='_NUMERO']`), depois regex na linha.
  Sem isso todas as OS caíam em `"000"/"desconhecida"` → ao pular UMA, TODAS
  eram ignoradas (`_puladas`).
- **Dry-run não pode ficar preso:** cada OS simulada é adicionada a `_puladas`
  para o loop avançar para a próxima (senão reencontra a mesma célula à toa).
- **Idempotência:** OS já faturada é **pulada** (`already` → `_puladas`).
- **União de condicionais** (`any_error_message`): **CSS-only** com `:has-text`.
  NÃO misturar engine `text=` com `:has-text` na mesma união (erro de format).
- **Texto de erro quebrado em tags:** usar `a:has-text(...)`, não `text=` puro.
- **Detecção de erros com espera única** (union) em vez de checagens curtas
  sequenciais (evita perder o diálogo tardio).
- **`TargetClosedError`:** importado de `playwright._impl._errors` e
  **relançado** de `process_all` para o retry global do runner (não engolir).
- **Skip:** após erro detectado, fechar **UMA vez** o dialog (volta à tabela e
  pula). Fechar **duas vezes** cai de volta no menu (indesejado).
- **Max tentativas por OS:** `MAX_TENTATIVAS = 3`; ao atingir, `failure`.
- **Dry-run:** sem `--full`, cada OS vira status `simulada` (sem clicar nada).
- **Overlays `noty`:** `.noty_modal`/`.noty_bar` interceptam cliques;
  `_dismiss_notifs()` fecha após ações (ex.: "NFS-e emitida").
- **Sessão 2FA:** após login válido, `storage_state` salvo; execuções seguintes
  reutilizam (sem 2FA repetido). Se expirar, o login pede o código de novo.

---

## 7. Modelos de status e dados

`WorkOrderResult.status` (ver `services/report.py`):
`success` | `via_sefaz` | `simulada` | `pulada` | `failure`.

- `success_count` = `success` + `via_sefaz`; `failure_count` = `failure`;
  `pulada_count` = `pulada`.
- Relatório Markdown com tabela por OS + etapas executadas; JSON equivalente.

---

## 8. Histórico de bugs/armadilhas resolvidas

| Problema                                  | Causa                                                             | Solução                                                                |
| ----------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Popup "Primeiros Passos" atrapalhava      | Abre APÓS entrar no módulo (conta Nucleo)                         | Fechar com "Fechar" antes de "Listar todas as"                        |
| Checklist "Conferindo..." exige OK        | Botão "OK" necessário para emitir                                 | Aguardar OK quando não há erro                                         |
| Skip caía no menu                         | Fechar o dialog 2 vezes                                           | Fechar UMA vez e pular                                                 |
| "falta preencher o X" (item específico)   | Não resolve via SEFAZ (ex.: Bairro)                               | MANTIDO: OS é pulada (decisão do usuário)                              |
| "Sim" não visível após Faturar Agora      | Overlay/notificação intercepta ou dialog demora                   | `_open_billing` re-tenta Faturar Agora→Sim até 3x dispensando overlays |
| Erro ao usar `text=` | Texto quebrado em várias tags | Usar `a:has-text(...)` |
| `os_number_cell` retornava coroutine | `header.evaluate` chamado sem `await` | Tornar `os_number_cell` `async` e aguardar no `_extract_os_id` |
| Retorno pós-faturamento inconsistente | Sucesso direto mantém a lista; sucesso via SEFAZ volta ao menu | `_refresh_list` aguarda células visíveis (caso direto) e senão reabre "Listar todas as" pelo menu |
| Erro de format na união de seletores      | Mistura de engine `text=` + CSS                                   | União CSS-only com `:has-text`                                         |
| Erros transitórios (rede/overlay/stale)   | Interceptação, rede instável                                      | `Waits.settle()` + `Waits.click()` com retry/backoff                  |
| Widget de grade (filtro situacao)         | Grade IgGrid com filterrow próprio                              | Seletores dedicados em `selectors/os.py`                               |
| Extração do número da OS                  | Texto da linha capturava R$/números errados                       | `os_number_cell` lê a coluna pelo header `th[id$='_NUMERO']` (fallback regex) |

---

## 9. Comandos de execução

```bash
# Ambiente
python -m venv .venv        # (se já não existir)
pip install -r requirements.txt
python -m playwright install chromium

# Loop completo na empresa Nucleo, sem tracing (uso diário)
python simulate_omie.py --full --no-trace --empresa Nucleo

# Com tracing (gera artefatos de inspeção em logs/simulacao/<ts>/)
python simulate_omie.py --full --empresa Nucleo

# Dry-run (inspeciona sem faturar)
python simulate_omie.py --no-trace --empresa Nucleo

# Ver trace gravado
python -m playwright show-trace logs/simulacao/<ts>/trace.zip

# CLI enxuta com relatório
python main_omie.py

# GUI (ex.: via .exe gerado por build_omie.bat)
python gui_omie.py
```

Artefatos de inspeção por rodada (`logs/simulacao/<timestamp>/`):
`trace.zip`, `fluxo.md` (etapas, URLs), `seletores.md` / `.json` (elementos
reais + validação dos seletores atuais).

---

## 10. Sendências / próximos passos

- **`automation/sefaz.py` + `selectors/sefaz.py`:** fora do loop atual — decidir
  se unificar com a correção inline de `faturamento.py` ou remover.
- **App root legado** (`main.py`, `gui.py`, `config.py`, `downloader.py`,
  `portal.py`, `utils.py`, `Rei_das_NFS.spec`, `installer.iss`, `build.bat`):
  referem-se ao outro projeto (exportação XML de notas fiscais) — fora do
  escopo da automação Omie. Não alterar junto.
- **`logs/sessao_omie.json`** com sessão expirada fará o login pedir 2FA de novo
  (comportamento esperado).
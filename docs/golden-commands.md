# Comandos dourados do Axel

Esta lista define os 20 fluxos principais que precisam continuar estaveis. Eles sao o contrato minimo para demo, TCC, portfolio e uso diario.

## Criterios

- O comando deve rotear para a action esperada.
- O comando deve validar sem erro.
- O risco deve estar explicito.
- A necessidade de confirmacao deve ser previsivel.
- Toda mudanca nesses comandos deve atualizar teste e documentacao.

## Lista v1

| # | Comando | Action esperada | Risco | Confirmacao | Status |
|---|---|---|---|---|---|
| 1 | `briefing` | `daily_briefing` | leitura | nao | pronto |
| 2 | `rotina diaria` | `daily_routine` | leitura | nao | pronto |
| 3 | `comecar meu dia` | `daily_routine` | leitura | nao | pronto |
| 4 | `clima em Salvador` | `weather_summary` | leitura | nao | pronto |
| 5 | `agenda de hoje` | `agenda_list_today` | leitura | nao | pronto |
| 6 | `lembretes` | `reminder_list` | leitura | nao | pronto |
| 7 | `status do telegram` | `telegram.status` | leitura | nao | pronto |
| 8 | `iniciar bot telegram` | `telegram.start_bot` | acao local | nao | pronto |
| 9 | `criar backup da memoria` | `memory.backup.create` via `action_tool_execute` | escrita local | nao | pronto |
| 10 | `listar backups da memoria` | `memory.backup.list` via `action_tool_execute` | leitura | nao | pronto |
| 11 | `abrir spotify` | `open_app` | acao local | nao | pronto |
| 12 | `fecha spotify` | `close_app` | alto | sim | pronto |
| 13 | `pausar musica` | `media_play_pause` | acao local | nao | pronto |
| 14 | `aumentar volume` | `volume_up` | acao local | nao | pronto |
| 15 | `nova aba` | `browser_new_tab` | acao local | nao | pronto |
| 16 | `role para baixo` | `browser_scroll_down` | acao local | nao | pronto |
| 17 | `status da visao` | `vision_status` | leitura | nao | pronto |
| 18 | `status das tarefas em segundo plano` | `background_status` | leitura | nao | pronto |
| 19 | `status do bluetooth` | `bluetooth_status` | leitura | nao | pronto |
| 20 | `listar arquivos` | `list_files` | leitura | nao | pronto |

## Lista v2: HUD e modos operacionais

Estes comandos nao passam pelo roteador principal; eles vivem em `ui_bridge` ou `work_mode_commands`. Por isso possuem teste dedicado em `tests/test_golden_ui_commands_v2.py`.

| # | Comando | Superficie | Resultado esperado | Risco | Status |
|---|---|---|---|---|---|
| 1 | `mostrar hud` | `ui_bridge` | interface visivel | acao local | pronto |
| 2 | `fechar hud` | `ui_bridge` | interface oculta | acao local | pronto |
| 3 | `status da interface` | `ui_bridge` | estado da interface | leitura | pronto |
| 4 | `saude do axel` | `ui_bridge` | painel de saude | leitura | pronto |
| 5 | `abrir painel de skills` | `ui_bridge` | painel de skills | leitura | pronto |
| 6 | `modo economia` | `work_mode` | performance economy | acao local | pronto |
| 7 | `modo equilibrado` | `work_mode` | performance balanced | acao local | pronto |
| 8 | `modo performance` | `work_mode` | performance mode | acao local | pronto |

## Fora da v2

Comandos com efeitos externos mais fortes, como escrita de arquivos, automacoes complexas e rotinas multi-etapas, devem entrar em listas futuras quando houver fallback, confirmacao e demo especificos.

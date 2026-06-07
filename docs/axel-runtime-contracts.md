# Axel Runtime Contracts

Este documento registra os contratos minimos entre roteamento, actions, memoria e background. A meta e impedir que o Axel cresca por acidente: cada modulo pode evoluir, mas precisa respeitar estas fronteiras.

## Principios

- O router decide intencao, nao executa efeito colateral.
- O normalizer transforma intencao em `Command`.
- O executor executa apenas `Command` validado.
- Actions expostas precisam estar registradas em `actions.registry`.
- Memorias locais devem usar leitura defensiva e escrita atomica.
- Background so roda actions seguras ou wrappers explicitamente revisados.
- Erros de navegador, arquivo, rede, visao e carteira devem passar pelo padrao de `core.action_errors`.

## Contrato De Command

Fonte: `core/command_schema.py`.

Campos:

- `action`: nome canonico da action registrada.
- `params`: argumentos ja normalizados para a action.
- `source`: origem logica, como `router`, `ui_bridge` ou macro.
- `confidence`: confianca do roteamento quando disponivel.
- `requires_confirmation`: sinal explicito para comandos sensiveis.

Regras:

- `Command` nao deve conter texto bruto quando o parametro ja tem nome especifico.
- Actions de arquivo, sistema, navegador clicavel, macro, restore e scripts precisam de confirmacao quando alteram estado.
- `action_tool_execute` deve receber `name` e `arguments`, mas nao pode chamar a si mesmo.

## Contrato De Router

Fontes principais: `core/router.py`, `core/router_registry.py`, `core/normalizer.py`.

Entrada:

- Texto do usuario ja recebido por voz, terminal ou UI.

Saida esperada:

- `None`, quando o detector nao reconhece.
- `dict` com `intent` e `target`, quando reconhece.
- Campos extras sao permitidos quando o normalizer conhece esses campos.

Formato recomendado:

```python
{"intent": "weather_summary", "target": "Salvador"}
{"intent": "investment_set_price_ceiling", "ticker": "PETR4", "price": "48"}
{"intent": "action_tool_execute", "target": {"name": "tool.name", "arguments": {}}}
```

Regras:

- Detectores devem ser baratos e deterministicos.
- Detector nao deve chamar IA externa, navegador, arquivo pesado ou rede.
- Grupos mais especificos devem vir antes de conversa generica.
- Todo novo intent precisa de caso correspondente em `core.normalizer`.
- Todo novo comando importante deve entrar nos golden tests quando tiver frase natural estavel.
- Grupos de detectores devem expor `intent_level`.
- Niveis canonicos: `comando_direto`, `pergunta`, `tarefa_composta` e `conversa`.
- O nivel de intencao deve aparecer na telemetria de roteamento.
- O nivel nao deve mudar o resultado da rota sozinho; ele orienta politica futura de ferramenta/modelo.
- A classificacao `simple_command` vs `complex_reasoning` deve ser calculada sem chamada de rede/modelo.
- Telemetria de rota deve incluir `complexity`, `complexity_reason`, `should_plan` e `should_use_llm`.

## Contrato De Action

Fonte: `actions/registry.py`.

Campos obrigatorios:

- `name`: nome unico.
- `description`: frase curta e operacional.
- `handler`: funcao que recebe `dict`.

Metadados:

- `category`: `browser`, `files`, `vision`, `investments`, `system`, `memory`, `briefing`, etc.
- `read_only`: `True` quando nao altera mundo externo nem memoria critica.
- `requires_confirmation`: `True` quando altera estado sensivel ou irreversivel.
- `parameters`: schema simples para o catalogo.

Retorno:

- Preferencial: `ActionResult.ok(...)` ou `ActionResult.failed(...)`.
- Aceito por compatibilidade: `str`.
- Excecoes sao capturadas pelo executor/registry e formatadas por categoria.

Regras:

- Handler nao deve pedir input interativo.
- Handler deve ser idempotente quando possivel.
- Action sensivel nao deve ser disparada pelo background generico.
- Action longa deve usar cache, background ou ambos.
- Action que depende de recurso externo deve retornar falha clara, nao stack trace cru.

## Contrato De MCP Futuro

Fonte planejada: `docs/mcp-integration-plan.md`.

Regras:

- MCP deve ser uma ponte para ferramentas externas, nao um substituto do router, normalizer ou executor.
- Toda capacidade MCP aprovada deve virar action registrada antes de executar.
- Actions vindas de MCP devem declarar `read_only`, `requires_confirmation`, categoria e parametros.
- Escrita, rede sensivel, processo e acesso amplo a arquivos ficam bloqueados por padrao.
- Diagnostico de MCP deve falhar de forma clara quando nenhum servidor estiver configurado.
- A primeira integracao real deve ser read-only e coberta por teste sem rede real.

## Contrato De Permissao

Fontes: `core/permission_policy.py`, `core/sandbox_policy.py`, `core/command_service.py`.

Niveis:

- `read`: leitura local ou consulta sem efeito colateral sensivel.
- `low`: efeito pequeno e reversivel.
- `medium`: exige confirmacao simples.
- `high`: exige confirmacao forte.
- `critical`: scripts, arquivos destrutivos, restore, startup do Windows e similares.

Regras:

- `requires_confirmation` no `Command` sempre prevalece.
- `ActionSpec.requires_confirmation` tambem exige confirmacao.
- Actions em categorias `files`, `system`, `browser` e `automation` com confirmacao tendem a confirmacao forte.
- Actions de `investments` que alteram carteira, watchlist, tese ou preco-teto exigem confirmacao forte.
- Confirmacao forte aceita somente a frase normalizada `confirmar`.
- Auto-background so aceita action `read_only` sem confirmacao.
- Sandbox logico deve classificar escopo como `read_only`, `filesystem`, `process`, `browser` ou `automation`.
- Actions destrutivas devem marcar `dry_run_recommended` na telemetria.

## Contrato De Auditoria Sensivel

Fontes: `memory/sensitive_audit.py`, `core/command_service.py`.

Regras:

- Actions com confirmacao, confirmacao forte, risco `high` ou risco `critical` devem gerar auditoria.
- Auditoria sensivel deve ficar em `memory/sensitive_action_audit.jsonl`.
- Eventos minimos: `command_execute_start` e `command_execute_end`.
- Payload deve incluir action, params, categoria, risco, sandbox e flags de confirmacao.
- Falha ao escrever auditoria nao deve derrubar a execucao principal.
- Arquivo de auditoria deve ter limite de crescimento.

## Contrato De Allowlist De Automacoes

Fonte: `memory/automation_allowlist.py`.

Regras:

- Automacoes confiaveis devem ser persistidas em `memory/automation_allowlist.json`.
- Nomes devem ser normalizados antes de comparar.
- Allowlist nao deve liberar action destrutiva por si so.
- Qualquer uso futuro para reduzir confirmacao precisa respeitar permissao, sandbox e auditoria.
- Lista deve tolerar arquivo ausente, corrompido ou com itens duplicados.

## Contrato De Aprendizado De Rotinas

Fonte: `memory/routine_learning.py`.

Regras:

- O Axel pode observar comandos roteados para detectar repeticao de sequencias.
- Intents de conversa, repeticao e execucao de rotina/macro nao devem virar candidato.
- Sequencia repetida deve gerar sugestao pendente, nao rotina automatica.
- Sugestao deve explicar que depende de aprovacao humana.
- Observacoes devem ter limite de crescimento.
- Notificacao visual pode anunciar sugestao, mas nao deve executar nada.

## Contrato De Rotinas

Fonte: `core/routine_execution.py`.

Regras:

- Toda rotina deve passar por dry-run/preflight antes da primeira action real.
- O dry-run deve rotear/processar todos os passos antes da execucao.
- Etapas invalidas ou sensiveis entram no resultado, mas nao executam.
- Etapas com sandbox `requires_confirmation` ou `dry_run_recommended` devem ser bloqueadas na rotina automatica.
- Rotinas podem receber passos em texto ou actions ja roteadas em `dict`.
- Uma falha ou bloqueio descoberto no fim da rotina nao deve impedir o preflight de classificar os passos anteriores.

## Contrato De Background

Fontes: `core/background_tasks.py`, `actions/background_actions.py`, `services/background_notification_service.py`.

Entrada:

- Nome da tarefa.
- Funcao sem argumentos que retorna mensagem final.

Estados:

- `queued`
- `running`
- `succeeded`
- `failed`

Saidas:

- Snapshot em memoria.
- Historico persistido em `memory/background_tasks.jsonl`.
- Notificacao consumivel por `background_notifications`.
- Notificacao visual automatica em `memory/ui_state.json` para tarefas finalizadas.

Regras:

- Historico persistido deve ter limite de linhas.
- Resultado final precisa caber em texto compacto.
- Falha deve virar `failed`, nao matar o processo principal.
- Wrappers como `background_daily_briefing` podem liberar actions conhecidas.
- `background.run_action` nao pode executar action sensivel sem wrapper explicito.
- Publicacao para UI deve passar por servico, nao por import direto no runner default.

## Contrato De Memoria Local

Fontes: `memory/json_store.py`, modulos em `memory/`.

Regras:

- JSON local deve ser lido com fallback seguro.
- Escrita deve ser atomica quando o arquivo representa estado persistente.
- Novos modulos devem depender do contrato `JsonStorage` ou das funcoes de compatibilidade em `memory.json_store`.
- Modulos de memoria devem validar formato basico antes de usar.
- Memorias criticas precisam estar no backup.
- Arquivos de runtime grandes, temporarios ou HTML bruto nao devem virar contexto automatico.

Padrao recomendado:

```python
payload = read_json_file(path, default, validator=lambda value: isinstance(value, dict))
write_json_atomic(path, payload, indent=2)
```

Backend atual:

- `LocalJsonStorage`: backend local com lock por arquivo e escrita atomica.
- `DEFAULT_JSON_STORAGE`: instancia padrao usada pelas funcoes legadas.

## Contrato De Memoria Conversacional

Fontes: `memory/session.py`, `memory/long_memory.py`, `llm/chat.py`.

Regras:

- Memoria curta da sessao deve ser em processo, limitada e limpa no startup/reset.
- API legada de `memory.session.add/get/clear` deve continuar compativel.
- Novos turnos estruturados devem registrar `role`, `text` e `source`.
- Memoria longa deve poder ser consultada por score sem chamada de rede/modelo.
- Score deve considerar termos coincidentes, confianca, repeticao e recencia.
- Prompt de conversa pode receber memorias longas relevantes, nao apenas as mais recentes.
- Busca sem termo util deve retornar lista vazia.

## Contrato De Cache

Fonte: `core/cache_policy.py`.

Regras:

- Cache deve ter TTL explicito.
- TTL e caminho canonicos devem vir de `CachePolicy`.
- Cache de tela precisa validar hash ou identificador de conteudo, nao apenas tempo.
- Cache de carteira deve ser invalidado quando refresh real ocorrer.
- Cache invalido ou corrompido deve ser ignorado silenciosamente.
- Novo cache persistente deve ser registrado em `KNOWN_CACHE_POLICIES`.

Caches atuais:

- `daily_briefing`: `memory/briefing_cache.json`, TTL de 15 minutos.
- `investment_summary`: `memory/investment_summary_cache.json`, TTL de 10 minutos.
- `investment_report`: `memory/investment_report_cache.json`, TTL de 10 minutos.
- `vision_screen`: `memory/vision_screen_cache.json`, TTL de 90 segundos, exige hash da tela.

## Contrato De Briefing De Startup

Fontes: `core/startup_briefing.py`, `tools/briefing_tools.py`.

Regras:

- Briefing de startup deve ser entregue no maximo uma vez por dia, salvo quando o usuario limpar estado/configuracao.
- O briefing pode ser adiado para thread de startup para nao travar o modo voz.
- O resumo diario deve conter saudacao, clima, agenda, carteira/radar, foco do dia e lembretes quando disponiveis.
- O foco do dia deve ser explicito, mesmo quando nao ha tarefa salva.
- Falha ao montar briefing nao deve impedir o Axel de iniciar.
- Cache de briefing pode ser usado, mas o conteudo precisa continuar adequado para startup.

## Contrato De Agenda E Lembretes

Fontes: `memory/agenda.py`, `memory/reminders.py`, `core/reminder_announcer.py`, `main.py`.

Regras:

- Agenda local deve continuar funcionando como lista simples quando o usuario informa apenas dia/texto.
- Quando o usuario informa horario, o compromisso deve salvar `due_at` e entrar no fluxo de avisos vencidos.
- Itens de agenda avisados devem ser marcados com `notified_at` para evitar repeticao.
- Lembretes e agenda podem compartilhar o anunciador, mas a fala deve diferenciar compromisso de lembrete.
- Briefing deve ler agenda sem depender do loop de avisos.
- Falha ao consumir agenda vencida nao deve impedir lembretes normais ou o runtime de voz.
- Exportacao/importacao ICS e ponte externa; `memory/agenda.json` continua sendo a fonte local canonica.
- Importacao ICS deve aceitar somente eventos simples com `SUMMARY` e `DTSTART`, ignorando blocos incompletos.
- Exportacao/importacao de calendario deve passar por action registrada e confirmacao, porque escreve arquivo ou altera agenda.

## Contrato De Estudos

Fontes: `memory/study.py`, `core/study_commands.py`, `actions/study_actions.py`, `ui/axel_web_hud.html`.

Regras:

- Estudos devem ficar separados de treino fisico.
- Estado persistente deve registrar metas, revisoes e sessoes de estudo.
- Revisoes devem aceitar data/horario quando informado e manter pendencias ate conclusao humana.
- Sessoes devem somar minutos do dia contra uma meta diaria configuravel.
- Painel de estudos deve ser alimentado por snapshot estruturado, nao por parsing do texto final.
- Comandos de estudo podem abrir o HUD e ativar o painel, mas nao devem bloquear o caminho quente da voz com tarefas pesadas.

## Contrato De Monitoramento De Carteira

Fontes: `services/investment_monitor_service.py`, `memory/investment_report.py`, `tools/investment_tools.py`.

Regras:

- Monitor proativo deve reaproveitar o radar local da carteira e as regras de preco-teto ja cadastradas.
- Alertas materiais incluem mudanca relevante de preco-teto, fatos/noticias relevantes, dividendos, volatilidade, vacancia e pontos de atencao.
- Sinais sem alerta forte nao devem gerar notificacao.
- Background de carteira pode rodar o monitor apos refresh, mas falha no monitor nao pode derrubar o refresh.
- Notificacao visual deve ser curta e marcada como investimento.
- Notificacao por voz so entra na fila quando o usuario habilitou notificacoes faladas.

## Contrato De WhatsApp Como Canal

Fontes: `services/whatsapp_gateway.py`, `services/whatsapp_webhook_server.py`, `tools/whatsapp_tools.py`, `actions/whatsapp_actions.py`.

Regras:

- WhatsApp comeca como canal de consulta ao Axel, nao como canal de envio para terceiros.
- Apenas remetentes em allowlist podem receber resposta.
- Entrada remota deve passar pelo router normal do Axel.
- Comandos de escrita, destrutivos ou que exigem confirmacao devem ser bloqueados no WhatsApp.
- A primeira versao aceita apenas respostas e actions de leitura.
- A ponte local pode ser iniciada por action/comando natural e deve responder status sem rede externa.
- Simulacao local deve permitir testar roteamento antes de conectar provedor real.
- Webhook local deve usar token quando exposto por tunel ou ponte externa.
- Se o PC estiver desligado, a ponte local nao responde; uma fila em nuvem pode ser adicionada depois.

## Contrato De Latencia

Fontes: `core/latency_metrics.py`, `core/command_service.py`, `core/response_pipeline.py`, `main.py`.

Regras:

- Toda medicao operacional deve publicar evento `latency_stage`.
- Campos minimos: `stage` e `duration_ms`.
- Stages canonicos atuais: `stt`, `routing`, `action`, `tts` e `output`.
- `stt` mede o ciclo de captura/transcricao percebido pelo runtime de voz.
- `routing` mede apenas deteccao/roteamento, sem execucao de action.
- `action` mede apenas a chamada da action foreground.
- `tts` mede despacho/sintese/reproducao conforme configuracao ativa de fala.
- `output` mede formatacao, UI, historico e fala da resposta final.
- Novas medicoes devem preservar esses nomes para comparacao historica.

## Contrato De Selecao De Modelo

Fontes: `llm/model_selection.py`, `llm/chat.py`, `llm/ollama_client.py`.

Regras:

- Selecao de IA textual deve produzir uma rota explicita com `provider`, `model`, `reason` e fallback.
- Providers canonicos: `local`, `cloud` e `auto`.
- Preferencia explicita do usuario/configuracao deve prevalecer quando segura e disponivel.
- Comando direto deve permanecer local por padrao.
- Pergunta, conversa ou tarefa composta complexa pode ir para nuvem quando configurada.
- Chamada marcada como `provider="local"` nao pode cair em Gemini por fallback implicito.
- Chamada marcada como `provider="cloud"` deve usar provedor remoto diretamente.
- Se nuvem falhar em conversa, o fallback permitido e o modelo local configurado.

## Contrato De Performance Runtime

Fontes: `core/performance_mode.py`, `core/terminal_voice_io.py`, `main.py`.

Regras:

- O intervalo ocioso do loop de hotword deve vir de `runtime_idle_sleep_seconds_from_state`.
- Modo economia deve dormir mais que o modo equilibrado.
- Modo silencioso/foco deve dormir mais que economia quando nao houver comando pendente.
- O polling de comandos do painel continua acontecendo antes do sono ocioso.
- O intervalo minimo de sono deve evitar busy loop mesmo com configuracao invalida.

## Contrato De Caminho Quente Da Voz

Fontes: `core/deferred_runtime.py`, `main.py`.

Regras:

- O caminho quente da voz deve priorizar captura, roteamento, execucao essencial e resposta.
- Efeitos colaterais nao criticos podem ser deferidos em thread daemon.
- Memoria conversacional derivada do texto falado nao deve bloquear a resposta de voz.
- Aprendizado de rotinas por repeticao nao deve bloquear roteamento de turnos por voz.
- Falha em tarefa deferida deve virar log, nao excecao no loop principal.
- Fluxos de texto/UI podem continuar sincronicos quando isso simplificar testes e previsibilidade.

## Contrato De UI/HUD

Fonte: `memory/ui_state.py`, `ui/qt_axel_hud.py`, `ui/axel_web_hud.html`.

Regras:

- Estado da UI passa por `memory/ui_state.json`.
- UI pode enviar comandos, mas nao executa actions diretamente.
- Painel deve tolerar campos ausentes e usar defaults.
- Modo economia deve reduzir polling e movimento sem quebrar controles.
- Notificacoes devem ser curtas e preservadas em lista limitada.
- Notificacoes falaveis ficam em `voice_notifications_pending` e devem respeitar modo silencioso/foco.

## Contrato De Notificacao Por Voz

Fonte: `services/voice_notification_service.py`.

Regras:

- Voz automatica deve ser opt-in por `voice_notifications_enabled`.
- Modo silencioso/foco bloqueia fala automatica.
- Falhas de background podem ser faladas quando opt-in estiver ativo.
- Sucesso so deve ser falado para tarefas importantes.
- O servico prepara fila falavel; a reproducao real fica no runtime de voz.
- O runtime consome no maximo uma notificacao falavel pendente por ciclo.
- O runtime nao remove item da fila quando o estado atual bloqueia fala automatica.

## Contrato De Personalidade E Resposta Curta

Fonte: `core/response_style.py`, `memory/assistant_phrases.py`.

Regras:

- A camada de estilo so deve atuar em respostas curtas, sem quebras de linha e sem estrutura tecnica.
- Mensagens estruturadas, diagnosticos, arquivos, erros e leituras longas devem passar sem reescrita cosmetica.
- Confirmacoes comuns devem ser curtas e variar por contexto.
- Abertura/fechamento de apps e estados de escuta devem usar variantes contextuais, nao frases fixas repetidas.
- A resposta final deve evitar repetir literalmente a ultima resposta estilizada quando houver estado disponivel.
- A personalidade nao deve adicionar explicacao extra a comandos simples; ela deve confirmar a acao de forma breve.

## Checklist Para Nova Feature

- Criou detector ou reusou intent existente?
- Normalizer converte para `Command`?
- Action esta registrada com categoria correta?
- Permissao e confirmacao fazem sentido?
- Existe teste de router, action ou golden command?
- Se for pesado, tem cache/background?
- Se falhar, a mensagem usa categoria correta?
- Se persistir estado, usa escrita atomica?
- Roadmap/backlog foi atualizado quando necessario?

## Contrato De Saude Textual

Fonte: `core/text_health.py`, `core/project_health.py`.

Regras:

- Diagnostico deve detectar sinais de mojibake antes de correcoes manuais.
- Arquivos temporarios, chunks externos, backups, `.git`, `venv` e `__pycache__` ficam fora da varredura.
- Painel de saude deve mostrar o primeiro arquivo suspeito e a contagem limitada.
- Correcao de encoding deve ser feita em blocos revisaveis, nao por substituicao global cega.

## Contrato De Verificacao De Startup

Fonte: `tools/system_tools.py`, `core/project_health.py`, `docs/axel-startup-verification.md`.

Regras:

- Diagnostico local valida atalho, conteudo esperado, logs e erros recentes.
- A prova final de abertura com Windows exige reboot real.
- Quando reboot ainda nao ocorreu, o status deve permanecer como verificacao pendente, nao como sucesso presumido.
- Checklist de startup deve ficar documentado para a validacao manual pos-reinicio.

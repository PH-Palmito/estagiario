# Prioridades do Axel

Este documento concentra as prioridades de maior ROI para deixar o Axel mais confiavel, demonstravel e util no dia a dia.

## Posicionamento

O Axel deve ser tratado como um copiloto operacional local para Windows: voz, automacao, navegador, memoria e seguranca para executar tarefas praticas no ambiente do operador.

Evitar, por enquanto, o posicionamento de agente autonomo generico. Esse posicionamento cria expectativa maior que o produto atual e dilui o diferencial local-first.

## Prioridade 1: confiabilidade operacional

Objetivo: o Axel precisa diagnosticar a si mesmo e deixar claro o que esta pronto, quebrado ou incompleto.

- Implementar `axel doctor`/`--doctor` como diagnostico geral. Status: concluido.
- Implementar `--backup-memory` como snapshot direto antes de refatoracoes. Status: concluido.
- Corrigir alerta de encoding/mojibake nos arquivos principais. Status: concluido.
- Tornar o `json_store` resiliente quando o arquivo temporario some antes do replace atomico. Status: concluido.
- Implementar `axel setup`/`--setup` como checklist de configuracao inicial. Status: concluido.
- Medir latencia de voz, roteamento, modelo, action e TTS. Status: parcial; STT, roteamento, actions e chamadas de modelo entram no log operacional, e `latencia do axel` mostra gargalos recentes e recomendacoes.
- Expor ultimos erros, actions lentas e integracoes incompletas. Status: parcial; `--doctor`/painel de saude mostram erros recentes, actions lentas, startup, background, integracoes e observabilidade.
- Manter logs locais legiveis e sem dados sensiveis desnecessarios. Status: parcial; `memory/execution_log.py` mascara chaves sensiveis e padroes comuns como bearer token, token inline, email, CPF e numeros longos.
- Criar scripts operacionais baratos fora do chat. Status: primeira camada concluida; `scripts/axel_action.py` chama actions por JSON e bloqueia escrita por padrao.
- Criar cache para sites frequentes. Status: primeira camada concluida; produtos listados no navegador geram `memory/browser_product_cache.json` e podem ser consultados por comando/action sem reler a tela.
- Criar resumo diario da carteira desde o ultimo snapshot. Status: concluido; `o que mudou na carteira desde ontem` compara o historico local, destaca patrimonio, rentabilidade, ativos com maior variacao, dividendos, preco-teto e noticias quando disponiveis.
- Reduzir acoplamento do navegador. Status: concluido na primeira camada; `tools/browser_tools.py` ficou como fachada, com dominios extraidos e contexto Windows isolado em `tools/browser_windows_context.py`.
- Avaliar MCP como camada futura. Status: concluido como decisao de arquitetura; MCP entra apenas como adapter para actions registradas, conforme `docs/mcp-integration-plan.md`.
- Integrar calendario real. Status: primeira camada concluida por ICS; `exportar calendario`, `importar calendario caminho.ics` e `status do calendario` criam ponte com Google Agenda, Outlook e Samsung Calendar sem OAuth.

## Prioridade 2: comandos dourados

Objetivo: ter poucos fluxos muito confiaveis em vez de muitas features medianas.

- Definir 20 comandos essenciais. Status: concluido na v1.
- Criar testes de smoke para esses comandos. Status: concluido na v1.
- Documentar cada comando com entrada, resultado esperado, risco e fallback. Status: parcial; entrada, action, risco e confirmacao documentados.
- Adicionar comandos de HUD e modos operacionais fora do router principal. Status: concluido na v2.
- Criar comandos compartilhados para terminal/HUD/Telegram. Status: parcial; `/status`, `/usage`, `/insights`, `/skills`, `/help`, `/model`, `/reset`, `/stop`, `/retry` e `/undo` estao na camada comum. Telegram fica em leitura/seguranca; local pode resetar conversa/HUD, cancelar pendencias, repetir ultimo comando e trocar preferencia de modelo. Undo ainda e conservador: cancela pendencias, mas nao promete reverter acoes ja executadas.
- Aceitar audio no Telegram. Status: primeira camada concluida; mensagens `voice`/`audio` sao reconhecidas, baixadas no polling e transcritas via Faster-Whisper quando o ambiente suporta.
- Reavaliar permissao remota alem de midia/volume. Status: concluido como decisao conservadora; `remote_permission_summary()` centraliza que remoto ampliado segue desativado, leitura segura pode executar, midia/volume leve exige confirmacao no chat e escrita/apps/arquivos/automacoes continuam no PC.
- Controlar LEDs do teclado. Status: primeira camada concluida; comandos de status, ligar, desligar e ajustar cor/perfil/efeito salvam estado em modo simulado/plugavel ate existir provedor fisico compativel.
- Usar esses comandos como demo principal do projeto.

## Prioridade 3: AxelBrain auditavel

Objetivo: transformar o AxelBrain em uma timeline clara de decisao.

- Registrar entrada, rota, intent, agente, toolset, risco, confirmacao, action e resultado. Status: concluido na v1 da timeline.
- Mostrar essa timeline no HUD. Status: concluido na v1; painel de contexto renderiza `axel_brain_timeline`.
- Permitir consultar a ultima decisao por texto. Status: parcial; `timeline do axelbrain` consulta as ultimas entradas.
- Separar decisao deterministica, contexto usado e resposta final. Status: parcial; a timeline agora salva blocos `decision`, `context`, `execution` e `response`, e o comando `timeline do axelbrain` mostra essa separacao.

## Prioridade 4: memoria com fontes

Objetivo: memoria deve ajudar sem virar ruido.

- Melhorar sugestoes de skills procedurais para evitar titulos genericos e duplicatas obvias. Status: concluido na v1.
- Cada memoria importante deve ter origem, data, validade, confianca e motivo. Status: parcial; memoria longa salva/exibe esses metadados e a nota Long Memory do Obsidian tambem mostra fonte, confianca, validade e motivo.
- Separar memoria curta, memoria episodica, preferencias e snapshots operacionais.
- Criar limpeza/deduplicacao periodica. Status: parcial; `limpar memoria longa` remove vencidas e mescla duplicatas exatas normalizadas.
- Mostrar quais memorias influenciaram uma resposta. Status: parcial; recall em camadas agora mostra fonte, confianca, validade e motivo das memorias longas usadas.
- Adotar contexto por workspace/projeto. Status: primeira camada concluida; `AGENTS.md`, `AXEL.md`, `.agents/AGENTS.md`, `.agents/AXEL.md` e `.axel/context.md` entram no contexto operacional.

## Prioridade 5: UX enxuta

Objetivo: o Axel deve parecer ferramenta diaria, nao catalogo de experimentos.

- Reduzir o HUD para status, ultimo comando, saude, AxelBrain, tarefas e confirmacoes. Status: parcialmente concluido; o painel de comandos virou uma primeira camada de command deck com busca, filtros por grupo e metricas de comandos visiveis.
- Enxugar o README para demo, instalacao, comandos principais, arquitetura e seguranca.
- Criar uma demo curta de 2 minutos com voz, navegador, Telegram e HUD.
- Empacotar fluxo de instalacao Windows quando os comandos dourados estiverem estaveis.

## Congelar por enquanto

Estes itens so devem voltar depois das prioridades acima:

- WhatsApp real.
- Discord como canal remoto principal; manter apenas como alternativa futura se o Telegram nao cobrir bem o uso remoto.
- Financas avancadas alem de snapshot/consulta basica.
- NewsAPI como feature central.
- Supabase e Obsidian como argumentos principais de produto.
- Novos provedores LLM sem necessidade operacional clara.
- Paineis visuais que nao ajudem no diagnostico ou execucao.

## Proximo passo imediato

Deixar o empacotamento Windows para a fase final, quando o projeto parar de mudar com tanta frequencia.

# Lista de fazeres do Axel

## Nucleo actions + file processor + memoria + tools

- [x] Criar catalogo de actions chamaveis por nome.
- [x] Encapsular treino como actions.
- [x] Encapsular investimentos como actions.
- [x] Criar file_processor inicial para texto, codigo, JSON e CSV/TSV.
- [x] Criar memoria simples por namespace e chave.
- [x] Criar tool_router para listar schemas e executar actions.
- [x] Conectar actions ao executor atual do Axel.
- [x] Adicionar fallback para escolher actions de leitura automaticamente.
- [x] Remover contrato duplicado do validator e validar actions pelo ActionSpec.
- [x] Criar requirements.txt com as dependencias atuais do venv.
- [x] Ampliar golden tests com comandos reais de voz do uso diario.
- [x] Corrigir encoding quebrado nos arquivos principais de fala, roteamento, visao, carteira e tarefas.
- [x] Criar comandos naturais para memoria simples, como lembrar, consultar e listar contexto.
- [x] Expandir file_processor para PDF, DOCX e XLSX.
- [x] Permitir executar actions com argumentos complexos pelo painel.
- [x] Adicionar confirmacao mais forte para actions de escrita sensiveis.
- [x] Extrair confirmation_flow do main.py.
- [x] Extrair command_service do main.py.
- [x] Remover inventario manual de ACTIONS do executor.
- [x] Separar ui_bridge do main.py.
- [ ] Separar voice_loop do main.py.
- [x] Separar app_bootstrap do main.py.
- [ ] Separar detectores do router por dominio.
- [ ] Corrigir residuos finais de encoding em memorias e docs.

- [x] Fazer o Axel iniciar junto com o Windows.
- [x] Criar um modo de auto avanco para o Axel pedir melhorias ao Codex.
- [x] Ensinar o Axel a analisar imagens e tirar informacoes uteis delas.
- [x] Ensinar o Axel a procurar erros em codigos com mais inteligencia.
- [x] Evoluir a visao para ler graficos com mais precisao quando houver modelo visual instalado.
- [x] Criar relatorio financeiro da carteira com patrimonio, rentabilidade, proventos e alertas.
- [x] Criar uma agenda local para compromissos do Axel.
- [x] Incluir agenda, clima e carteira em um briefing diario.
- [x] Evoluir o briefing com alertas mais proativos, noticias e agenda mais inteligente.
- [x] Reduzir a saudacao de startup no modo voz/painel para evitar texto colado antes do briefing.
- [x] Criar modo de leitura visual por clipboard, tela, navegador e arquivo com historico das ultimas analises.
- [ ] Continuar evoluindo a interface para algo ainda mais futurista e animado.
- [ ] Redesenhar a interface como um command deck complexo, rico em informacoes e visualmente denso.
- [x] Ler texto selecionado na tela e traduzir quando eu pedir.
- [x] Criar confirmacao inteligente para comandos provaveis quando a transcricao vier ruim.
- [x] Criar memoria de correcoes automatica para o Axel aprender variacoes de voz sem mapear tudo manualmente.
- [x] Evoluir modo musica com comandos como gostei dessa, nao gostei, mais desse estilo e menos triste agora.
- [ ] Criar cache e fast path para Mercado Livre e sites frequentes, nos mesmos moldes do Spotify.
- [ ] Integrar o Axel ao WhatsApp para ler, resumir e enviar mensagens com confirmacao.
- [ ] Integrar o Axel a uma agenda/calendario real para criar, consultar e sincronizar compromissos.
- [x] Tratar buscas provaveis no YouTube, como "aqueles caras no YouTube", com confirmacao inteligente.

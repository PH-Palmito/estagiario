# WORKING

## Missao atual

Transformar o Axel em um mordomo local realmente util:

- rapido no uso diario
- conversavel
- com opiniao honesta
- com memoria util
- com automacao segura
- com carteira, agenda, clima, arquivos e navegador trabalhando juntos

## Estado atual em 2026-05-16

- comandos locais: funcionando e cobertos por golden tests
- actions: catalogo central criado e conectado ao executor
- validacao: migrando para ActionSpec, com contratos legados ainda em reducao
- voz: utilizavel, com correcoes e variacoes melhores, mas ainda sensivel a transcricao ruim
- investimentos: bem mais modular, com noticias, dividendos, preco-teto, watchlist, tese e relatorio
- briefing: fechado em formato curto, com clima, agenda, dividendos proximos, radar e patrimonio/rentabilidade
- memoria: memoria simples por namespace, memoria longa, contexto operacional e sync opcional
- file processor: base pronta para texto, codigo, JSON, CSV/TSV, PDF, DOCX e XLSX
- UI: painel funcional, com caminho aberto para command deck mais denso
- testes: suite unittest ativa, validando comandos, actions e carteira

## Foco desta fase

### 1. Consolidar o nucleo de actions

- remover dependencias restantes de tabelas legadas no validator
- manter ActionSpec como fonte unica de verdade
- garantir que cada action tenha categoria, parametros, leitura/escrita e confirmacao
- gerar mapa de capacidades a partir do catalogo

### 2. Reduzir acoplamento do main.py

- extrair command_service
- extrair confirmation_flow
- extrair voice_loop
- extrair ui_bridge
- deixar main.py como bootstrap e orquestrador fino

### 3. Melhorar robustez do uso real

- ampliar golden tests com frases reais de voz
- revisar logs de execucao para detectar comandos que confundem
- criar painel de saude do Axel
- padronizar mensagens de erro e recuperacao

### 4. Evoluir carteira e briefing

- manter noticias sem repeticao e com relevancia melhor
- criar resumo "o que mudou desde ontem"
- separar alertas por nivel: informativo, atencao, importante, critico
- refinar dividendos proximos, fatos relevantes e preco-teto

## Proximos passos imediatos

- finalizar a remocao do contrato duplicado de actions no validator/executor
- revisar encoding restante em arquivos de fala, docs e testes
- transformar main.py em modulos menores
- criar dashboard de saude: testes, ultimos erros, APIs, memoria, carteira e modelo de voz
- ampliar file_processor com exemplos reais de PDF, DOCX e XLSX
- criar command deck para executar actions com argumentos complexos pelo painel
- integrar agenda/calendario real quando a agenda local estiver estavel

## Backlog bom para depois

- cache e fast path para Mercado Livre e sites frequentes
- integracao com WhatsApp com confirmacao forte
- mapa geografico consultavel na UI
- modo treino de voz dentro do painel
- automacoes proativas de revisao diaria
- pesquisa com fontes e citacoes para perguntas abertas

## Nao fazer agora

- recolocar visao pesada sem necessidade clara
- acoplar banco ao loop principal
- transformar uma integracao externa no nucleo do Axel
- adicionar features grandes antes de estabilizar o nucleo de actions e o main.py

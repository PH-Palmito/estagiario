# Pedido de implementacao para o Codex

**Status:** ready_for_codex
**Titulo:** Executar proposta de patch: Lapidar robustez geral do Axel

## Mensagem
Codex, aplique este handoff no projeto Axel.

Objetivo: Executar proposta de patch: Lapidar robustez geral do Axel.
Status atual da aplicacao: applied.
Risco estimado: Baixo..

Arquivos alvo:
- main.py
- ui/assistant_hud.py

Instrucoes de implementacao:
- Leia os arquivos alvo antes de editar.
- Aplique a menor mudanca util possivel.
- Nao altere comportamento fora do escopo da acao candidata.
- Preserve mudancas existentes do usuario.
- Continuar instrumentando o historico para detectar melhor os proximos pontos fracos.
- Manter a ponte com o Codex atualizada com dados do uso recente.

Validacao sugerida:
- .\venv\Scripts\python.exe -m py_compile .\main.py .\ui/assistant_hud.py
- .\venv\Scripts\python.exe .\main.py --voice --hotword

Definicao de pronto:
- Arquivos alvo foram alterados apenas quando necessario.
- Validacao sugerida foi executada ou a impossibilidade foi registrada.
- Resultado foi explicado de forma curta para o operador.
- Se falhar, registrar a falha para alimentar nova rodada do Axel.

Regras:
- Leia os arquivos antes de editar.
- Use a menor mudanca util possivel.
- Preserve mudancas existentes do usuario.
- Ao terminar, diga exatamente o que mudou, como validou e se existe risco restante.

# Handoff do Axel para o Codex

**Status:** ready
**Titulo:** Executar proposta de patch: Lapidar robustez geral do Axel
**Risco:** Baixo.

## Arquivos alvo
- main.py
- ui/assistant_hud.py

## Instrucoes
- Leia os arquivos alvo antes de editar.
- Aplique a menor mudanca util possivel.
- Nao altere comportamento fora do escopo da acao candidata.
- Preserve mudancas existentes do usuario.
- Continuar instrumentando o historico para detectar melhor os proximos pontos fracos.
- Manter a ponte com o Codex atualizada com dados do uso recente.

## Validacao
- `.\venv\Scripts\python.exe -m py_compile .\main.py .\ui/assistant_hud.py`
- `.\venv\Scripts\python.exe .\main.py --voice --hotword`

## Definicao de pronto
- Arquivos alvo foram alterados apenas quando necessario.
- Validacao sugerida foi executada ou a impossibilidade foi registrada.
- Resultado foi explicado de forma curta para o operador.
- Se falhar, registrar a falha para alimentar nova rodada do Axel.
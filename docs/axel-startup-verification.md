# Axel Startup Verification

Este checklist fecha a parte que nao da para provar sem reiniciar o Windows.

## Antes de reiniciar

- Rode o comando natural: `status iniciar junto com o Windows`.
- O resultado esperado deve dizer que a inicializacao esta ativada e o atalho esta atualizado.
- Se aparecer atalho desatualizado, rode `python main.py --install-startup` ou use o comando do Axel para ativar inicializacao.

## Depois de reiniciar

- Verifique se o painel do Axel abriu.
- Verifique se o modo voz/hotword iniciou.
- Rode novamente: `status iniciar junto com o Windows`.
- Confirme que os logs existem:
  - `.tmp/axel-startup.log`
  - `.tmp/axel-startup-output.log`
- Se houver erro recente, o painel de saude deve mostrar o alerta.

## Criterio de pronto

- Atalho atualizado.
- Log de diagnostico criado.
- Log de saida criado.
- Nenhum `Traceback`, `PermissionError`, `Falha fatal`, `Error:` ou `Exception` recente.
- Axel abriu automaticamente apos o reboot real.

# MCP Como Camada Futura

MCP deve ser tratado como ponte para ferramentas externas, nao como novo nucleo do Axel.

## Decisao

- Manter `actions.registry`, `Command`, `permission_policy`, auditoria e confirmacoes como fronteira canonica.
- Usar MCP somente atras de adapters que exponham actions registradas.
- Bloquear por padrao qualquer ferramenta MCP com escrita, rede sensivel, execucao de processo ou acesso amplo a arquivos.
- Preferir RPC local (`scripts/axel_action.py`) para automacoes baratas dentro do proprio projeto.

## Quando Usar MCP

- Conectar ferramentas externas com contrato pronto, como calendario, notas, banco local, navegador dedicado ou IDE.
- Ler dados de sistemas que mudam fora do Axel.
- Expor catalogo de recursos quando a ferramenta ja tem permissao propria e escopo claro.

## Quando Evitar

- Comandos que o Axel ja executa bem via action local.
- Fluxos sensiveis sem allowlist, auditoria e confirmacao.
- Ferramentas que exigem credencial ampla sem escopo por recurso.
- Substituir roteadores deterministas por chamadas genericas de ferramenta.

## Modelo De Adapter

1. Descobrir recursos/ferramentas MCP.
2. Converter apenas capacidades aprovadas em actions registradas.
3. Marcar `read_only`, `requires_confirmation`, categoria e parametros.
4. Passar toda execucao pelo normalizer, validator, permission policy e executor.
5. Registrar resultado e erro no log operacional.

## Criterios Para Primeira Integracao

- Deve resolver um item de alto valor que hoje depende de conta externa, como calendario real.
- Deve ter escopo minimo: leitura primeiro, escrita depois com confirmacao forte.
- Deve ter teste unitario do adapter sem chamar rede real.
- Deve falhar com mensagem clara quando o servidor MCP nao estiver configurado.

## Ordem Recomendada

1. Adapter read-only experimental para listar recursos MCP configurados.
2. Action `mcp.status` para diagnostico.
3. Primeiro conector real somente para calendario/notas, com leitura.
4. Escrita apenas depois de allowlist, auditoria sensivel e confirmacao forte.

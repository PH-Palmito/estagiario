# Actions, file processor, memoria e tools

Esta camada acrescenta um nucleo chamavel por tools sem remover o fluxo antigo do Axel.

## Fluxo

```text
LLM ou roteador
  -> core.tool_router
    -> actions.registry
      -> action especifica
        -> memoria, file_processor, tools existentes ou APIs
```

## Onde fica cada parte

- `actions/`: catalogo de actions novas e wrappers para capacidades existentes.
- `file_processor/`: deteccao de tipo de arquivo e extracao inicial, incluindo texto/codigo, JSON, CSV/TSV, PDF simples, DOCX e XLSX.
- `memory/action_memory.py`: memoria simples por namespace/chave.
- `core/tool_router.py`: lista schemas e executa actions pelo nome.
- `tools/action_tools.py`: adaptador para o executor atual.

## Dominios ja encapsulados

- `training.*`: wrappers sobre `memory/training.py`.
- `investment.*`: wrappers sobre `tools/investment_tools.py`.
- `image_analyze_graph`: leitura de graficos por arquivo usando OCR, geometria e modelo visual quando instalado.
- `image_analyze_screen_graph`: leitura de graficos na tela com o mesmo modo especializado.
- `file.process`: deteccao e leitura inicial de arquivos.
- `memory.*`: lembrar, consultar e listar memorias simples.

## Exemplo em Python

```python
from core.tool_router import execute_tool, tool_catalog_text

print(tool_catalog_text("training"))
print(execute_tool("training.today", {}))
print(execute_tool("memory.remember", {
    "namespace": "projects",
    "key": "axel_core",
    "value": "Actions + file_processor + memoria + tools adicionados."
}))
```

# Política de caches e artefatos em `memory/`

O diretório `memory/` mistura dois tipos de arquivo:

- código versionável, como `memory/*.py`;
- estado local do Axel, como preferências, filas, snapshots, logs, caches e dumps de páginas.

Por padrão, só o código e a documentação intencional devem ir para o Git. Arquivos gerados em runtime ficam locais porque podem conter dados pessoais, carteira, histórico de uso, contexto visual, filas de comando ou páginas capturadas.

## O que fica fora do Git

- `memory/*.json` e `memory/*.jsonl`: estado local, snapshots, filas, preferências e logs estruturados;
- `memory/*.md`: notas geradas pelo Axel, exceto `memory/todo.md`;
- `memory/*.tmp`: arquivos temporários usados em escrita atômica;
- `memory/*.html`, `memory/*.txt` e `memory/*.playwright.txt`: dumps de navegador, carteira e páginas inspecionadas;
- `memory/obsidian_vault/`: vault local com notas pessoais;
- `memory/audio_diagnostics/`, `memory/chunks/` e `memory/map_cache/`: diagnósticos, bundles e caches.

## O que pode ir para o Git

- `memory/*.py`: módulos de leitura, escrita e interpretação da memória;
- `memory/todo.md`: lista operacional explícita do projeto;
- documentação em `docs/`.

## Antes de publicar

Se algum artefato local já estiver rastreado, o `.gitignore` não remove sozinho. Remova apenas do índice do Git, mantendo os arquivos no disco:

```powershell
git rm --cached memory/*.tmp
git rm --cached memory/*.html
git rm --cached memory/*.txt
git rm --cached memory/*.playwright.txt
```

Faça isso só depois de revisar se nenhum desses arquivos precisa virar fixture de teste ou documentação.

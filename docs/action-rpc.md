# RPC Local de Actions

O script `scripts/axel_action.py` permite chamar actions registradas do Axel sem passar pelo chat.

Uso basico:

```powershell
.\venv\Scripts\python.exe scripts\axel_action.py --list
.\venv\Scripts\python.exe scripts\axel_action.py --list --category memory
.\venv\Scripts\python.exe scripts\axel_action.py memory.backup.list --arg limit=3
.\venv\Scripts\python.exe scripts\axel_action.py memory.backup.list --json "{""limit"": 3}"
.\venv\Scripts\python.exe scripts\axel_action.py memory.backup.list --schema
```

Seguranca:

- Actions `read_only` rodam por padrao.
- Actions de escrita ou que exigem confirmacao ficam bloqueadas por padrao.
- `--allow-write` existe apenas para scripts locais confiaveis.
- A saida sempre e JSON, para facilitar automacoes baratas e repetiveis.

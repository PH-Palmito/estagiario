from __future__ import annotations

from actions.registry import ActionSpec, register_action
from memory.memory_backup import create_memory_backup, list_memory_backups, restore_memory_file


def _create_backup(_args):
    result = create_memory_backup()
    return (
        f"Backup de memoria criado: {result.backup_dir.name}. "
        f"Arquivos copiados: {len(result.copied)}; ausentes: {len(result.skipped)}."
    )


def _list_backups(args):
    backups = list_memory_backups(limit=int(args.get("limit") or 5))
    if not backups:
        return "Nenhum backup de memoria encontrado."
    rows = [
        f"{index}. {item.get('name')} ({item.get('files_count', 0)} arquivos)"
        for index, item in enumerate(backups, start=1)
    ]
    return "Backups de memoria: " + " ; ".join(rows) + "."


def _restore_backup_file(args):
    filename = str(args.get("filename") or "").strip()
    backup_name = str(args.get("backup_name") or "").strip()
    restored = restore_memory_file(filename, backup_name)
    return f"Arquivo de memoria restaurado: {restored.name} a partir de {backup_name}."


def register_memory_backup_actions() -> None:
    register_action(
        ActionSpec(
            name="memory.backup.create",
            description="Cria um snapshot dos arquivos criticos de memoria local.",
            handler=_create_backup,
            category="memory",
            read_only=False,
            requires_confirmation=False,
        )
    )
    register_action(
        ActionSpec(
            name="memory.backup.list",
            description="Lista snapshots recentes de memoria local.",
            handler=_list_backups,
            category="memory",
            read_only=True,
            parameters={
                "limit": {"type": "number", "description": "Quantidade maxima de backups."},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.backup.restore_file",
            description="Restaura um arquivo critico de memoria a partir de um backup.",
            handler=_restore_backup_file,
            category="memory",
            read_only=False,
            requires_confirmation=True,
            parameters={
                "backup_name": {"type": "string", "description": "Nome do snapshot.", "required": True},
                "filename": {"type": "string", "description": "Arquivo critico a restaurar.", "required": True},
            },
        )
    )

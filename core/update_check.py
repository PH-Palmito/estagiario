from __future__ import annotations

from pathlib import Path


def build_update_snapshot(root: Path | None = None) -> dict:
    project_dir = root or Path(__file__).resolve().parents[1]
    git_dir = project_dir / ".git"
    backup_dir = project_dir / "memory" / "backups"
    backups = []
    if backup_dir.exists():
        backups = sorted([item.name for item in backup_dir.iterdir() if item.is_dir()])

    steps = [
        "criar backup de memoria com --backup-memory",
        "rodar --doctor para registrar a saude antes da atualizacao",
        "conferir git status e revisar mudancas locais",
        "atualizar codigo somente depois de preservar trabalho local",
        "rodar testes focados e depois smoke dos comandos dourados",
        "rodar --doctor novamente apos a atualizacao",
    ]
    blockers = []
    if not git_dir.exists():
        blockers.append("diretorio .git nao encontrado")

    return {
        "status": "pronto para plano manual" if not blockers else "precisa de revisao",
        "root": str(project_dir),
        "git_repo": git_dir.exists(),
        "backup_count": len(backups),
        "latest_backup": backups[-1] if backups else "",
        "steps": steps,
        "blockers": blockers,
    }


def format_update_report(snapshot: dict | None = None) -> str:
    data = snapshot or build_update_snapshot()
    parts = [f"Update do Axel: {data.get('status', 'indefinido')}."]
    if data.get("git_repo"):
        parts.append("Repositorio Git detectado.")
    else:
        parts.append("Repositorio Git nao detectado.")

    backup_count = int(data.get("backup_count") or 0)
    latest_backup = str(data.get("latest_backup") or "").strip()
    if backup_count:
        parts.append(f"Backups de memoria: {backup_count}; ultimo: {latest_backup}.")
    else:
        parts.append("Backups de memoria: nenhum encontrado; rode --backup-memory antes de atualizar.")

    blockers = data.get("blockers") or []
    if blockers:
        parts.append("Pendencias: " + "; ".join(str(item) for item in blockers) + ".")

    steps = data.get("steps") or []
    if steps:
        formatted = " ; ".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
        parts.append("Plano seguro: " + formatted + ".")
    parts.append("Atualizacao automatica ainda nao esta liberada; este comando apenas prepara o procedimento.")
    return " ".join(parts)

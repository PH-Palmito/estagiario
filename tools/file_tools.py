import shutil
from pathlib import Path

BASE_DIR = Path.home() / "Documents"
BASE_DIR.mkdir(parents=True, exist_ok=True)


def safe_path(path_str: str):
    path = (BASE_DIR / path_str).resolve()
    base = BASE_DIR.resolve()

    if path != base and base not in path.parents:
        return None

    return path


def create_file(path_str: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return f"Arquivo criado: {path.name}"
    except Exception as e:
        return f"Erro ao criar arquivo: {e}"


def write_file(path_str: str, content: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Arquivo salvo: {path.name}"
    except Exception as e:
        return f"Erro ao escrever arquivo: {e}"


def append_file(path_str: str, content: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Conteúdo adicionado em: {path.name}"
    except Exception as e:
        return f"Erro ao adicionar conteúdo: {e}"


def replace_in_file(path_str: str, old_text: str, new_text: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    if not path.exists():
        return "Arquivo não encontrado."

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return "Texto alvo não encontrado no arquivo."

        updated = content.replace(old_text, new_text, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)

        return f"Texto substituído em: {path.name}"
    except Exception as e:
        return f"Erro ao substituir texto: {e}"


def read_file(path_str: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    if not path.exists():
        return "Arquivo não encontrado."

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if len(content) > 500:
            content = content[:500] + "\n... (truncado)"

        return content or "Arquivo vazio."
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


def list_files(folder: str = ""):
    path = safe_path(folder or "")
    if not path:
        return "Acesso negado."

    path.mkdir(parents=True, exist_ok=True)

    items = list(path.iterdir())
    if not items:
        return "Pasta vazia."

    output = []
    for item in items[:20]:
        prefix = "[DIR]" if item.is_dir() else "[ARQ]"
        output.append(f"{prefix} {item.name}")

    return "\n".join(output)


def delete_file(path_str: str):
    path = safe_path(path_str)
    if not path:
        return "Acesso negado."

    if not path.exists():
        return "Arquivo não encontrado."

    try:
        if path.is_dir():
            shutil.rmtree(path)
            return f"Pasta removida: {path.name}"
        else:
            path.unlink()
            return f"Arquivo removido: {path.name}"
    except Exception as e:
        return f"Erro ao remover: {e}"


def copy_file(src: str, dst: str):
    src_path = safe_path(src)
    dst_path = safe_path(dst)

    if not src_path or not dst_path:
        return "Acesso negado."

    if not src_path.exists():
        return "Arquivo de origem não encontrado."

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return f"Copiado para {dst_path.name}"
    except Exception as e:
        return f"Erro ao copiar: {e}"


def move_file(src: str, dst: str):
    src_path = safe_path(src)
    dst_path = safe_path(dst)

    if not src_path or not dst_path:
        return "Acesso negado."

    if not src_path.exists():
        return "Arquivo de origem não encontrado."

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        return f"Movido para {dst_path.name}"
    except Exception as e:
        return f"Erro ao mover: {e}"


def rename_file(src: str, new_name: str):
    src_path = safe_path(src)
    if not src_path:
        return "Acesso negado."

    if not src_path.exists():
        return "Arquivo não encontrado."

    try:
        new_path = src_path.with_name(new_name)
        src_path.rename(new_path)
        return f"Renomeado para {new_name}"
    except Exception as e:
        return f"Erro ao renomear: {e}"
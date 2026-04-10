import pyperclip


def get_clipboard():
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def set_clipboard(text: str):
    try:
        pyperclip.copy(text)
        return "Copiado para a área de transferência."
    except Exception as e:
        return f"Erro ao copiar: {e}"
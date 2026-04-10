import re


def format_number(value: float):
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def calculate_percentage(text: str):
    """
    Entende frases como:
    - 10% de 200
    - 15 por cento de 80
    """

    normalized = text.lower().strip().replace(",", ".")

    match = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*(?:de|por cento de)\s*(\d+(?:\.\d+)?)", normalized)
    if not match:
        return None

    percent = float(match.group(1))
    value = float(match.group(2))

    result = (percent / 100) * value

    return f"{format_number(percent)}% de {format_number(value)} é {format_number(result)}."


def calculate_basic_expression(text: str):
    """
    Entende expressões simples como:
    - 1+1
    - 10 - 3
    - 4*5
    - 8 / 2
    """

    normalized = text.lower().strip().replace(",", ".")
    normalized = normalized.replace(" ", "")

    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)([+\-*/])(-?\d+(?:\.\d+)?)", normalized)
    if not match:
        return None

    a = float(match.group(1))
    op = match.group(2)
    b = float(match.group(3))

    try:
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            if b == 0:
                return "Não é possível dividir por zero."
            result = a / b
        else:
            return None
    except Exception:
        return None

    return f"{format_number(a)} {op} {format_number(b)} = {format_number(result)}."
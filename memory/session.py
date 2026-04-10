history = []


def add(message: str):
    history.append(message)

    if len(history) > 10:
        del history[0]


def get():
    return history[-3:]


def clear():
    history.clear()
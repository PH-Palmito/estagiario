from __future__ import annotations

from collections.abc import Callable


def browser_read_more(
    *,
    activate_browser_window: Callable[[], bool],
    mouse_wheel: Callable[[int], None],
    describe_screen: Callable[[], str],
    sleep: Callable[[float], None],
) -> str:
    if not activate_browser_window():
        return "Nao encontrei um navegador aberto para ler mais."

    mouse_wheel(-550)
    sleep(0.25)
    result = describe_screen()

    if result.startswith("Vejo na tela:"):
        return result.replace("Vejo na tela:", "Mais abaixo vejo:", 1)

    if result.startswith("Consegui ler texto da pagina:"):
        return result.replace("Consegui ler texto da pagina:", "Mais abaixo consegui ler:", 1)

    return result

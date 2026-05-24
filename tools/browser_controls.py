from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class BrowserControls:
    activate_browser_window: Callable[[], bool]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    click: Callable[[int, int], None]
    get_browser_window_rect: Callable[[], tuple[int, int, int, int] | None]
    click_first_browser_link: Callable[[], bool]
    click_browser_element_by_text: Callable[[str], bool]
    type_text: Callable[[str], None]
    open_url: Callable[..., object]
    keybd_event: Callable[..., None]
    mouse_event: Callable[..., None]
    keyup_flag: int
    mouse_wheel_flag: int
    vk_control: int
    vk_shift: int
    vk_menu: int
    vk_tab: int
    vk_w: int
    vk_l: int
    vk_f: int
    vk_f5: int
    vk_add: int
    vk_subtract: int
    vk_0: int
    vk_return: int
    vk_prior: int
    vk_next: int
    vk_end: int
    vk_home: int
    vk_left: int
    vk_right: int
    sleep: Callable[[float], None] = time.sleep

    def new_tab(self) -> str:
        if self.activate_browser_window():
            self.shortcut(self.vk_control, 0x54)
            return "Abrindo nova aba."

        self.open_url("https://www.google.com", new=2)
        return "Abrindo nova aba."

    def close_tab(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para fechar a aba."

        self.shortcut(self.vk_control, self.vk_w)
        return "Fechando aba."

    def next_tab(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para trocar de aba."

        self.shortcut(self.vk_control, self.vk_tab)
        return "Indo para a proxima aba."

    def prev_tab(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para trocar de aba."

        self.shortcut(self.vk_control, self.vk_shift, self.vk_tab)
        return "Voltando para a aba anterior."

    def back(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para voltar."

        self._alt_tap(self.vk_left)
        return "Voltando pagina."

    def forward(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para avancar."

        self._alt_tap(self.vk_right)
        return "Avancando pagina."

    def refresh(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para atualizar."

        self.tap(self.vk_f5)
        return "Atualizando pagina."

    def open_first_result(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para abrir o resultado."

        if self.click_first_browser_link():
            return "Abrindo primeiro resultado."

        self.tap(self.vk_tab)
        self.sleep(0.08)
        self.tap(self.vk_return)
        return "Abrindo primeiro resultado."

    def open_focused_item(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para abrir."

        self.tap(self.vk_return)
        return "Abrindo item selecionado."

    def click_center(self) -> str:
        rect = self.get_browser_window_rect()
        if not rect:
            return "Nao encontrei um navegador aberto para clicar."

        left, top, right, bottom = rect
        self.click(left + ((right - left) / 2), top + ((bottom - top) / 2))
        return "Clicando no centro da pagina."

    def click_text(self, query: str) -> str:
        if not query:
            return "Clicar em que texto?"

        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para clicar."

        if self.click_browser_element_by_text(query):
            return f"Clicando em {query}."

        return f"Nao encontrei {query} visivel na pagina."

    def zoom_in(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para zoom."

        self.shortcut(self.vk_control, self.vk_add)
        return "Aumentando zoom."

    def zoom_out(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para zoom."

        self.shortcut(self.vk_control, self.vk_subtract)
        return "Diminuindo zoom."

    def zoom_reset(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para zoom."

        self.shortcut(self.vk_control, self.vk_0)
        return "Restaurando zoom."

    def search(self, query: str) -> str:
        if not query:
            return "Qual termo voce quer pesquisar?"

        if not self.activate_browser_window():
            self.open_url(f"https://www.google.com/search?q={quote_plus(query)}", new=2)
            return f"Pesquisando por {query} em uma nova aba."

        self.shortcut(self.vk_control, self.vk_l)
        self.sleep(0.05)
        self.type_text(query)
        self.tap(self.vk_return)
        return f"Pesquisando por {query} na aba atual."

    def find(self, query: str) -> str:
        if not query:
            return "Qual texto voce quer procurar na pagina?"

        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para procurar na pagina."

        self.shortcut(self.vk_control, self.vk_f)
        self.sleep(0.05)
        self.type_text(query)
        self.tap(self.vk_return)
        return f"Procurando {query} na pagina."

    def scroll_down(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.tap(self.vk_next)
        return "Rolando para baixo."

    def scroll_down_small(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.mouse_event(self.mouse_wheel_flag, 0, 0, -350, 0)
        return "Descendo um pouco."

    def scroll_up(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.tap(self.vk_prior)
        return "Rolando para cima."

    def scroll_up_small(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.mouse_event(self.mouse_wheel_flag, 0, 0, 350, 0)
        return "Subindo um pouco."

    def scroll_top(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.tap(self.vk_home)
        return "Indo para o topo."

    def scroll_bottom(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para rolar."

        self.tap(self.vk_end)
        return "Indo para o fim."

    def _alt_tap(self, vk_code: int) -> None:
        self.keybd_event(self.vk_menu, 0, 0, 0)
        self.sleep(0.02)
        self.tap(vk_code)
        self.keybd_event(self.vk_menu, 0, self.keyup_flag, 0)

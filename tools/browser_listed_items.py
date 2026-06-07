from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from memory.browser_product_cache import cached_product_items, cheapest_cached_product, describe_cached_product


def short_click_query(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"\bR\$\s*[\d\.\,]+.*$", "", normalized, flags=re.IGNORECASE).strip()
    words = normalized.split()

    if len(words) > 8:
        normalized = " ".join(words[:8])

    return normalized


def click_query_variants(text: str) -> list[str]:
    base = short_click_query(text)
    if not base:
        return []

    words = [word for word in base.split() if word]
    variants = []

    def add_variant(candidate: str):
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
        if len(candidate) >= 3 and candidate not in variants:
            variants.append(candidate)

    add_variant(base)

    for size in (6, 5, 4, 3):
        if len(words) >= size:
            add_variant(" ".join(words[:size]))

    if "-" in base:
        add_variant(base.split("-", 1)[0])

    return variants


def click_browser_item_from_text(text: str, click_browser_element_by_text: Callable[[str], bool]) -> bool:
    for query in click_query_variants(text):
        if click_browser_element_by_text(query):
            return True
    return False


def extract_brl_price(text: str):
    matches = re.findall(r"R\$\s*([\d\.]+,\d{2})", text or "", flags=re.IGNORECASE)
    if not matches:
        return None

    values = []
    for match in matches:
        try:
            values.append(float(match.replace(".", "").replace(",", ".")))
        except ValueError:
            continue

    if not values:
        return None

    return min(values)


@dataclass
class BrowserListedItemCommands:
    activate_browser_window: Callable[[], bool]
    refresh_browser_context: Callable[[], str]
    listed_browser_elements: Callable[[], list]
    describe_screen: Callable[[], str]
    click_page_item_by_text: Callable[[str], bool]
    click_browser_item_from_text: Callable[[str], bool]
    browser_find: Callable[[str], str]
    click: Callable[[int, int], None]
    sleep: Callable[[float], None]

    def click_listed_item(self, index: int) -> str:
        if index < 1:
            return "Qual item da lista?"

        if self.activate_browser_window():
            self.refresh_browser_context()

        elements = self.listed_browser_elements()
        if index > len(elements):
            self.describe_screen()
            elements = self.listed_browser_elements()

        if index > len(elements):
            return "Li a tela, mas nao encontrei esse item na lista atual."

        item = elements[index - 1]
        if item.get("x") is None or item.get("y") is None:
            if self.click_page_item_by_text(item["text"]):
                return f"Tentando abrir o item {index}: {item['text']}."

            query = short_click_query(item["text"])

            if self.click_browser_item_from_text(item["text"]):
                return f"Clicando no item {index}: {item['text']}."

            if query:
                self.browser_find(query)
                self.sleep(0.12)
                if self.click_browser_item_from_text(item["text"]):
                    return f"Clicando no item {index}: {item['text']}."
                return (
                    f"Encontrei o texto do item {index}, mas nao consegui clicar direto nele. "
                    "Deixei ele procurado na pagina."
                )

            return "Tenho esse item em texto, mas nao consegui transformar em clique."

        self.click(item["x"], item["y"])
        return f"Clicando no item {index}: {item['text']}."

    def describe_listed_item(self, index: int) -> str:
        if index < 1:
            return "Qual item?"

        if self.activate_browser_window():
            self.refresh_browser_context()

        elements = self.listed_browser_elements()
        if index > len(elements):
            cached = cached_product_items()
            if cached:
                return describe_cached_product(index)
            return "Ainda nao tenho esse item na lista. Selecione os produtos e diga: ler selecionado."

        item = elements[index - 1]
        return f"Item {index}: {item['text']}."

    def cheapest_listed_item(self) -> str:
        if self.activate_browser_window():
            self.refresh_browser_context()

        elements = self.listed_browser_elements()
        if not elements:
            if cached_product_items():
                return cheapest_cached_product()
            self.describe_screen()
            elements = self.listed_browser_elements()

        priced_items = []
        for index, item in enumerate(elements, start=1):
            price = extract_brl_price(item.get("text", ""))
            if price is None or price <= 0:
                continue
            priced_items.append((price, index, item["text"]))

        if not priced_items:
            return "Ainda nao tenho precos claros na lista atual. Tente dizer: o que tem na tela."

        _price, index, text = min(priced_items, key=lambda entry: entry[0])
        return f"O mais barato que encontrei e o item {index}: {text}."

import urllib.parse

from tools.system_tools import open_url


def google_search(query: str):
    encoded = urllib.parse.quote_plus(query)
    open_url(f"https://www.google.com/search?q={encoded}")
    return f"Pesquisando por {query} no Google."


def open_chatgpt():
    return open_url("https://chat.openai.com/")

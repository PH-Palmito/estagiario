from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.browser_tools import (
    browser_back,
    browser_cheapest_listed_item,
    browser_click_center,
    browser_click_listed_item,
    browser_click_text,
    browser_close_tab,
    browser_describe_listed_item,
    browser_describe_screen,
    browser_explain_screen,
    browser_find,
    browser_forward,
    browser_investment_snapshot,
    browser_music_session,
    browser_new_tab,
    browser_next_tab,
    browser_open_first_result,
    browser_open_focused_item,
    browser_open_wallet_and_summarize,
    browser_prev_tab,
    browser_queue_music,
    browser_read_more,
    browser_read_selected_products,
    browser_read_selection,
    browser_refresh,
    browser_scroll_bottom,
    browser_scroll_down,
    browser_scroll_down_small,
    browser_scroll_top,
    browser_scroll_up,
    browser_scroll_up_small,
    browser_search,
    browser_search_music,
    browser_search_site,
    browser_summarize_screen,
    browser_surprise_music,
    browser_translate_last_selection,
    browser_translate_selection,
    browser_zoom_in,
    browser_zoom_out,
    browser_zoom_reset,
    spotify_diagnostic,
    spotify_dislike_current_track,
    spotify_less_music_vibe,
    spotify_like_current_track,
    spotify_more_like_current_track,
)


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    read_only: bool = False,
    requires_confirmation: bool = False,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="browser",
            read_only=read_only,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def register_legacy_browser_actions() -> None:
    query_param = {"query": {"type": "string", "description": "Texto de busca ou alvo.", "required": True}}
    index_param = {"index": {"type": "integer", "description": "Indice do item.", "required": True}}
    site_query_params = {
        "site": {"type": "string", "description": "Site alvo.", "required": True},
        "query": {"type": "string", "description": "Busca no site.", "required": True},
    }
    service_query_params = {
        "service": {"type": "string", "description": "Servico de musica.", "required": True},
        "query": {"type": "string", "description": "Busca musical.", "required": True},
    }

    _register("browser_new_tab", "Abre nova aba.", lambda _args: browser_new_tab())
    _register("browser_close_tab", "Fecha aba atual.", lambda _args: browser_close_tab(), requires_confirmation=True)
    _register("browser_next_tab", "Vai para proxima aba.", lambda _args: browser_next_tab())
    _register("browser_prev_tab", "Vai para aba anterior.", lambda _args: browser_prev_tab())
    _register("browser_back", "Volta no navegador.", lambda _args: browser_back())
    _register("browser_forward", "Avanca no navegador.", lambda _args: browser_forward())
    _register("browser_refresh", "Atualiza pagina atual.", lambda _args: browser_refresh())
    _register("browser_open_first_result", "Abre primeiro resultado visivel.", lambda _args: browser_open_first_result())
    _register("browser_open_focused_item", "Abre item focado.", lambda _args: browser_open_focused_item())
    _register("browser_click_center", "Clica no centro da tela.", lambda _args: browser_click_center(), requires_confirmation=True)
    _register("browser_click_text", "Clica em texto visivel.", lambda args: browser_click_text(args.get("query", "")), query_param, requires_confirmation=True)
    _register("browser_click_listed_item", "Clica em item listado.", lambda args: browser_click_listed_item(args.get("index")), index_param, requires_confirmation=True)
    _register("browser_describe_listed_item", "Descreve item listado.", lambda args: browser_describe_listed_item(args.get("index")), index_param, read_only=True)
    _register("browser_cheapest_listed_item", "Identifica item listado mais barato.", lambda _args: browser_cheapest_listed_item(), read_only=True)
    _register("browser_describe_screen", "Descreve tela do navegador.", lambda _args: browser_describe_screen(), read_only=True)
    _register("browser_explain_screen", "Explica tela do navegador.", lambda _args: browser_explain_screen(), read_only=True)
    _register("browser_summarize_screen", "Resume tela do navegador.", lambda _args: browser_summarize_screen(), read_only=True)
    _register("browser_investment_snapshot", "Lê snapshot de investimentos no navegador.", lambda _args: browser_investment_snapshot(), read_only=True)
    _register("browser_open_wallet_and_summarize", "Abre carteira e resume dados.", lambda _args: browser_open_wallet_and_summarize())
    _register("browser_read_selection", "Lê seleção atual.", lambda _args: browser_read_selection(), read_only=True)
    _register("browser_read_selected_products", "Lê produtos selecionados.", lambda _args: browser_read_selected_products(), read_only=True)
    _register("browser_translate_last_selection", "Traduz ultima seleção.", lambda _args: browser_translate_last_selection(), read_only=True)
    _register("browser_translate_selection", "Traduz seleção atual.", lambda _args: browser_translate_selection(), read_only=True)
    _register("browser_read_more", "Continua leitura do navegador.", lambda _args: browser_read_more(), read_only=True)
    _register("browser_search", "Pesquisa no navegador.", lambda args: browser_search(args.get("query", "")), query_param)
    _register("browser_find", "Busca texto na pagina.", lambda args: browser_find(args.get("query", "")), query_param, read_only=True)
    _register("browser_scroll_down", "Rola para baixo.", lambda _args: browser_scroll_down())
    _register("browser_scroll_down_small", "Rola pouco para baixo.", lambda _args: browser_scroll_down_small())
    _register("browser_scroll_up", "Rola para cima.", lambda _args: browser_scroll_up())
    _register("browser_scroll_up_small", "Rola pouco para cima.", lambda _args: browser_scroll_up_small())
    _register("browser_scroll_top", "Vai ao topo.", lambda _args: browser_scroll_top())
    _register("browser_scroll_bottom", "Vai ao fim.", lambda _args: browser_scroll_bottom())
    _register("browser_zoom_in", "Aumenta zoom.", lambda _args: browser_zoom_in())
    _register("browser_zoom_out", "Diminui zoom.", lambda _args: browser_zoom_out())
    _register("browser_zoom_reset", "Restaura zoom.", lambda _args: browser_zoom_reset())
    _register("browser_search_site", "Pesquisa dentro de site.", lambda args: browser_search_site(args.get("site", ""), args.get("query", "")), site_query_params)
    _register("browser_search_music", "Pesquisa musica.", lambda args: browser_search_music(args.get("service", ""), args.get("query", "")), service_query_params)
    _register("browser_surprise_music", "Toca sugestao musical.", lambda args: browser_surprise_music(args.get("service", "spotify")), {"service": {"type": "string", "description": "Servico de musica."}})
    _register(
        "browser_music_session",
        "Inicia sessao musical por clima.",
        lambda args: browser_music_session(args.get("service", "spotify"), args.get("vibe", "")),
        {
            "service": {"type": "string", "description": "Servico de musica."},
            "vibe": {"type": "string", "description": "Clima musical.", "required": True},
        },
    )
    _register("browser_queue_music", "Coloca musica na fila.", lambda args: browser_queue_music(args.get("service", ""), args.get("query", "")), service_query_params)
    _register("spotify_diagnostic", "Diagnostica Spotify.", lambda _args: spotify_diagnostic(), read_only=True)
    _register("spotify_like_current_track", "Marca faixa atual como curtida.", lambda _args: spotify_like_current_track())
    _register("spotify_dislike_current_track", "Marca faixa atual como nao curtida.", lambda _args: spotify_dislike_current_track())
    _register("spotify_more_like_current_track", "Pede mais musicas parecidas.", lambda _args: spotify_more_like_current_track())
    _register("spotify_less_music_vibe", "Pede menos de um clima musical.", lambda args: spotify_less_music_vibe(args.get("vibe", "")), {"vibe": {"type": "string", "description": "Clima musical."}})

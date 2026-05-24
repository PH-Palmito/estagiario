from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, quote_plus

from tools.spotify_api import (
    spotify_add_to_queue,
    spotify_current_playback,
    spotify_next_track,
    spotify_remove_saved_track,
    spotify_save_track,
    spotify_search_track,
    spotify_search_tracks,
    spotify_start_playback,
)

SPOTIFY_TRACK_SEARCH_PREFIX = "track:"
SPOTIFY_LIKED_SONGS_QUERIES = {
    "curtidas",
    "minhas curtidas",
    "as curtidas",
    "musicas curtidas",
    "minhas musicas curtidas",
    "as musicas curtidas",
    "musicas que eu curti",
    "playlist musicas curtidas",
    "liked songs",
    "liked song",
}
SPOTIFY_SURPRISE_QUERIES = (
    "Everybody Wants To Rule The World Tears For Fears",
    "September Earth Wind Fire",
    "Lovely Day Bill Withers",
    "Sultans Of Swing Dire Straits",
    "The Less I Know The Better Tame Impala",
    "Get Lucky Daft Punk",
    "Feeling Good Nina Simone",
    "Take Five Dave Brubeck",
    "Oceano Djavan",
    "Ainda Bem Marisa Monte",
    "Tempo Perdido Legiao Urbana",
    "Lanterna Dos Afogados Os Paralamas Do Sucesso",
    "Back In Black AC/DC",
    "Sweet Child O Mine Guns N Roses",
    "No Surprises Radiohead",
    "Good Days SZA",
    "Lose Yourself Eminem",
    "Clair De Lune Debussy",
    "A Horse With No Name America",
    "Billie Jean Michael Jackson",
)
SPOTIFY_SESSION_QUEUE_TARGET = 5
SPOTIFY_MUSIC_SESSION_POOLS = {
    "alegre": ("September Earth Wind Fire", "Lovely Day Bill Withers", "Walking On Sunshine Katrina And The Waves"),
    "calmo": ("Oceano Djavan", "Ainda Bem Marisa Monte", "Clair De Lune Debussy", "No Surprises Radiohead"),
    "rock": ("Back In Black AC/DC", "Sultans Of Swing Dire Straits", "Sweet Child O Mine Guns N Roses", "Everlong Foo Fighters"),
    "classico": ("Clair De Lune Debussy", "Nocturne Op 9 No 2 Chopin", "The Four Seasons Spring Vivaldi"),
    "mpb": ("Oceano Djavan", "Ainda Bem Marisa Monte", "Lanterna Dos Afogados Os Paralamas Do Sucesso"),
    "jazz": ("Take Five Dave Brubeck", "Feeling Good Nina Simone", "So What Miles Davis"),
    "gospel": ("Filho Meu Thalles Roberto", "Eu Sou De Jesus Luma Elpidio", "Ninguem Explica Deus Preto No Branco"),
    "pop": ("Billie Jean Michael Jackson", "Blinding Lights The Weeknd", "As It Was Harry Styles"),
    "eletronica": ("Get Lucky Daft Punk", "Strobe Deadmau5", "One More Time Daft Punk"),
    "rap": ("Lose Yourself Eminem", "Alright Kendrick Lamar", "Juicy The Notorious B.I.G."),
    "samba": ("Deixa A Vida Me Levar Zeca Pagodinho", "Trem Das Onze Demonios Da Garoa", "O Mundo E Um Moinho Cartola"),
    "sertanejo": ("Evidencias Chitaozinho E Xororo", "Infiel Marilia Mendonca", "Cuida Bem Dela Henrique E Juliano"),
    "foco": ("Weightless Marconi Union", "Intro The xx", "Dayvan Cowboy Boards Of Canada"),
    "treino": ("Lose Yourself Eminem", "Till I Collapse Eminem", "Eye Of The Tiger Survivor"),
    "triste": ("No Surprises Radiohead", "Someone Like You Adele", "The Night We Met Lord Huron"),
}
SPOTIFY_MUSIC_SESSION_LABELS = {
    "alegre": "alegre",
    "calmo": "calma",
    "rock": "rock",
    "classico": "classica",
    "mpb": "MPB",
    "jazz": "jazz",
    "gospel": "gospel",
    "pop": "pop",
    "eletronica": "eletronica",
    "rap": "rap",
    "samba": "samba e pagode",
    "sertanejo": "sertaneja",
    "foco": "de foco",
    "treino": "de treino",
    "triste": "melancolica",
}


@dataclass
class BrowserMusic:
    normalize_text: Callable[[str], str]
    os_startfile: Callable[[str], object]
    sleep: Callable[[float], None]
    focus_app: Callable[[str], object]
    open_url: Callable[..., object]
    click_track_by_name: Callable[[str], bool]
    click_first_visible_track: Callable[[], bool]

    def search_music(self, service: str, query: str) -> str:
        if not query:
            return "Qual musica voce quer procurar?"

        service = (service or "").lower().strip()
        normalized_query = self.normalize_text(query)

        if service == "spotify":
            if normalized_query in SPOTIFY_LIKED_SONGS_QUERIES:
                try:
                    self.os_startfile("spotify:collection:tracks")
                    self.sleep(1.0)
                    self.focus_app("spotify")
                    return "Abrindo suas musicas curtidas no Spotify."
                except Exception:
                    self.open_url("https://open.spotify.com/collection/tracks")
                    return "Abrindo suas musicas curtidas no Spotify."

            try:
                best_track = spotify_search_track(query)
            except Exception:
                best_track = None

            if best_track:
                return self.play_track_result(query, best_track)

            try:
                spotify_query = f"{SPOTIFY_TRACK_SEARCH_PREFIX}{query}"
                self.os_startfile(f"spotify:search:{quote(spotify_query)}")
                self.sleep(1.2)
                self.focus_app("spotify")
                return f"Abrindo a busca por {query} no Spotify."
            except Exception:
                self.open_url(f"https://open.spotify.com/search/{quote_plus(query)}")
                return f"Abrindo a busca por {query} no Spotify."

        self.open_url(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
        return f"Procurando {query} no YouTube."

    def surprise_music(self, service: str = "spotify") -> str:
        service = (service or "spotify").lower().strip()
        if service != "spotify":
            return "Por enquanto, o modo surpresa musical esta preparado para o Spotify."
        return self.start_session(SPOTIFY_SURPRISE_QUERIES, "surpresa", surprise=True)

    def music_session(self, service: str = "spotify", vibe: str = "") -> str:
        service = (service or "spotify").lower().strip()
        if service != "spotify":
            return "Por enquanto, sessoes por clima e genero estao preparadas para o Spotify."

        normalized_vibe = self.normalize_text(vibe)
        queries = SPOTIFY_MUSIC_SESSION_POOLS.get(normalized_vibe)
        if not queries:
            return f"Ainda nao tenho uma sessao pronta para {vibe}. Posso tocar uma musica especifica se voce quiser."

        label = SPOTIFY_MUSIC_SESSION_LABELS.get(normalized_vibe, normalized_vibe)
        return self.start_session(queries, label)

    def queue_music(self, service: str, query: str) -> str:
        if not query:
            return "Qual musica voce quer adicionar a fila?"

        service = (service or "").lower().strip()
        if service != "spotify":
            return "Por enquanto, fila automatica so esta preparada para o Spotify."

        try:
            best_track = spotify_search_track(query)
        except Exception:
            best_track = None

        if not best_track:
            return f"Nao encontrei {query} no Spotify para colocar na fila."

        track_uri = str(best_track.get("uri") or "").strip()
        track_name = str(best_track.get("name") or query).strip()
        track_artists = str(best_track.get("artists") or "").strip()
        if track_uri and spotify_add_to_queue(track_uri):
            if track_artists:
                return f"Adicionei {track_name}, de {track_artists}, a fila do Spotify."
            return f"Adicionei {track_name} a fila do Spotify."

        return (
            "Encontrei a musica, mas ainda nao consigo adicionar a fila sem o OAuth do Spotify com permissao de playback. "
            "Posso abrir ou tocar a faixa por enquanto."
        )

    def like_current_track(self) -> str:
        current, message = self._current_track_or_message()
        if not current:
            return message

        track_id = str(current.get("id") or "").strip()
        label = spotify_track_label(current, "a musica atual")
        if track_id and spotify_save_track(track_id):
            return f"Gostei do seu gosto. Salvei {label} nas suas musicas curtidas."
        return f"Encontrei {label}, mas nao consegui salvar nas curtidas agora."

    def dislike_current_track(self) -> str:
        current, message = self._current_track_or_message()
        if not current:
            return message

        track_id = str(current.get("id") or "").strip()
        label = spotify_track_label(current, "essa faixa")
        removed = bool(track_id and spotify_remove_saved_track(track_id))
        skipped = spotify_next_track()

        if removed and skipped:
            return f"Entendido. Tirei {label} das curtidas, se estava la, e pulei para a proxima."
        if skipped:
            return f"Entendido. Pulei {label}. Vamos tentar algo melhor."
        if removed:
            return f"Entendido. Tirei {label} das curtidas, se estava la."
        return f"Entendi que {label} nao agradou, mas nao consegui alterar o playback agora."

    def more_like_current_track(self) -> str:
        current, message = self._current_track_or_message()
        if not current:
            return message

        artists = str(current.get("artists") or "").strip()
        primary_artist = artists.split(",")[0].strip()
        if not primary_artist:
            return "Eu ouvi a faixa atual, mas nao consegui identificar o artista para montar algo parecido."

        try:
            tracks = spotify_search_tracks(f'artist:"{primary_artist}"', limit=6)
        except Exception:
            tracks = []

        current_id = str(current.get("id") or "").strip()
        tracks = [track for track in tracks if str(track.get("id") or "") != current_id]
        if not tracks:
            return f"Tentei puxar mais musicas parecidas com {primary_artist}, mas nao encontrei uma fila boa agora."

        first = tracks[0]
        started = bool(first.get("uri") and spotify_start_playback(str(first.get("uri"))))
        if not started:
            started = self.play_track_via_app(str(first.get("name") or primary_artist), str(first.get("name") or ""), str(first.get("artists") or ""))

        queued = []
        for track in tracks[1:SPOTIFY_SESSION_QUEUE_TARGET]:
            if track.get("uri") and spotify_add_to_queue(str(track.get("uri"))):
                queued.append(track)

        if started:
            response = f"Seguindo essa linha: tocando {spotify_track_label(first)}."
            if queued:
                response += f" Tambem deixei mais {len(queued)} faixas parecidas na fila."
            return response

        return self.play_track_result(str(first.get("name") or primary_artist), first)

    def less_music_vibe(self, vibe: str = "") -> str:
        normalized = self.normalize_text(vibe)
        alternatives = {
            "triste": ("alegre", "menos melancolica"),
            "melancolico": ("alegre", "menos melancolica"),
            "melancolica": ("alegre", "menos melancolica"),
            "agitado": ("calmo", "mais calma"),
            "agitada": ("calmo", "mais calma"),
            "pesado": ("calmo", "mais leve"),
            "pesada": ("calmo", "mais leve"),
        }
        target_vibe, label = alternatives.get(normalized, ("calmo", "mais equilibrada"))
        queries = SPOTIFY_MUSIC_SESSION_POOLS.get(target_vibe)
        if not queries:
            return "Consigo ajustar o clima, mas ainda nao tenho uma sessao alternativa pronta para isso."
        return self.start_session(queries, label)

    def play_track_via_app(self, query: str, track_name: str = "", track_artists: str = "") -> bool:
        search_query = track_name or query
        if track_artists:
            search_query = f"{search_query} {track_artists}"
        try:
            self.os_startfile(f"spotify:search:{quote(SPOTIFY_TRACK_SEARCH_PREFIX + search_query)}")
            self.sleep(1.4)
            self.focus_app("spotify")
            self.sleep(0.4)
            if self.click_track_by_name(track_name or query):
                return True
            return self.click_first_visible_track()
        except Exception:
            return False

    def play_track_result(self, query: str, best_track: dict, *, surprise: bool = False) -> str:
        track_uri = str(best_track.get("uri") or "").strip()
        track_id = str(best_track.get("id") or "").strip()
        track_name = str(best_track.get("name") or query).strip()
        track_artists = str(best_track.get("artists") or "").strip()

        if track_uri and spotify_start_playback(track_uri):
            return _format_play_response("tocando", track_name, track_artists, surprise=surprise)

        if self.play_track_via_app(query, track_name, track_artists):
            return _format_play_response("tentando tocar", track_name, track_artists, surprise=surprise)

        try:
            if track_id:
                self.os_startfile(f"spotify:track:{track_id}")
            elif track_uri:
                self.os_startfile(track_uri)
            else:
                raise RuntimeError("track_not_found")
            self.sleep(1.4)
            self.focus_app("spotify")
        except Exception:
            track_url = str(best_track.get("url") or "").strip()
            if track_url:
                self.open_url(track_url)
        return _format_play_response("abrindo", track_name, track_artists, surprise=surprise)

    def search_session_tracks(self, queries, limit: int = SPOTIFY_SESSION_QUEUE_TARGET) -> list[dict]:
        tracks = []
        seen = set()
        query_list = list(queries or [])
        if not query_list:
            return tracks

        for query in random.sample(query_list, k=len(query_list)):
            try:
                track = spotify_search_track(query)
            except Exception:
                track = None
            if not track:
                continue

            key = str(track.get("uri") or track.get("id") or track.get("name") or query).casefold()
            if key in seen:
                continue
            seen.add(key)
            tracks.append(track)
            if len(tracks) >= limit:
                break

        return tracks

    def start_session(self, queries, label: str, *, surprise: bool = False) -> str:
        tracks = self.search_session_tracks(queries)
        if not tracks:
            return f"Tentei montar uma sessao {label} no Spotify, mas nao encontrei faixas agora."

        first_track = tracks[0]
        first_uri = str(first_track.get("uri") or "").strip()
        started = bool(first_uri and spotify_start_playback(first_uri))
        if not started:
            started = self.play_track_via_app(
                str(first_track.get("name") or ""),
                str(first_track.get("name") or ""),
                str(first_track.get("artists") or ""),
            )

        if not started:
            return self.play_track_result(str(first_track.get("name") or label), first_track, surprise=surprise)

        queued = []
        for track in tracks[1:]:
            track_uri = str(track.get("uri") or "").strip()
            if track_uri and spotify_add_to_queue(track_uri):
                queued.append(track)

        prefix = "Surpresa escolhida" if surprise else f"Sessao {label} iniciada"
        response = f"{prefix}: tocando {spotify_track_label(first_track)}."
        if queued:
            response += f" Tambem deixei mais {len(queued)} faixas na fila."
        elif len(tracks) > 1:
            response += " Encontrei outras faixas, mas nao consegui adicionar a fila agora."
        return response

    def _current_track_or_message(self):
        current = spotify_current_playback()
        if not current or not current.get("name"):
            return None, "Nao identifiquei uma musica tocando agora no Spotify."
        return current, ""


def spotify_track_label(track: dict, fallback: str = "a faixa escolhida") -> str:
    name = str(track.get("name") or fallback).strip()
    artists = str(track.get("artists") or "").strip()
    if artists:
        return f"{name}, de {artists}"
    return name


def _format_play_response(verb: str, track_name: str, track_artists: str, *, surprise: bool = False) -> str:
    verb_text = verb.capitalize()
    if surprise:
        verb_text = f"Surpresa escolhida: {verb}"
    if track_artists:
        return f"{verb_text} {track_name}, de {track_artists}, no Spotify."
    return f"{verb_text} {track_name} no Spotify."

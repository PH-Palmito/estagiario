import base64
import ctypes
import hashlib
import json
import msvcrt
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import time
import wave
import winsound
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

import difflib
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError
from llm.gemini_tts_client import synthesize_gemini_tts_to_wav
from memory.voice_preferences import load_voice_preferences
from scipy.io.wavfile import read as read_wav
from scipy.io.wavfile import write as write_wav


POWERSHELL_EXE = "powershell"
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
SAMPLE_RATE = 16000
COMMAND_MODEL_SIZE = "small"
HOTWORD_MODEL_SIZE = "tiny"
FRAME_SIZE = 1024
DEFAULT_MAX_RECORD_SECONDS = 6.0
VOICE_PREFERENCES = load_voice_preferences()
CONVERSATION_MODEL_SIZE = str(VOICE_PREFERENCES.get("conversation_model_size", COMMAND_MODEL_SIZE))
TTS_PRONUNCIATIONS_PATH = Path("memory") / "tts_pronunciations.json"
_PIPER_WORKER_LOCK = Lock()
_PIPER_WORKER_PROCESS = None
_PIPER_WORKER_SIGNATURE = None
_PIPER_WORKER_SAMPLE_RATE = 22050
_PIPER_WORKER_WARM = False
_TTS_WAIT_FOR_PLAYBACK_OVERRIDE = None


def _float_pref(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(VOICE_PREFERENCES.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def _int_pref(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(VOICE_PREFERENCES.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


DEFAULT_MIN_SPEECH_SECONDS = _float_pref("audio_min_speech_seconds", 0.25, 0.05, 2.0)
DEFAULT_MAX_SILENCE_SECONDS = _float_pref("audio_max_silence_seconds", 0.75, 0.2, 3.0)
SILENCE_THRESHOLD = _float_pref("audio_silence_threshold", 0.01, 0.001, 0.2)
AUDIO_DYNAMIC_THRESHOLD = bool(VOICE_PREFERENCES.get("audio_dynamic_threshold", True))
AUDIO_NOISE_MULTIPLIER = _float_pref("audio_noise_multiplier", 3.0, 1.2, 10.0)
AUDIO_MAX_DYNAMIC_THRESHOLD = _float_pref("audio_max_dynamic_threshold", 0.04, 0.005, 0.3)
AUDIO_PREROLL_SECONDS = _float_pref("audio_preroll_seconds", 0.25, 0.0, 1.0)
AUDIO_NORMALIZE_ENABLED = bool(VOICE_PREFERENCES.get("audio_normalize_enabled", True))
AUDIO_DC_OFFSET_FILTER = bool(VOICE_PREFERENCES.get("audio_dc_offset_filter", True))
AUDIO_TARGET_PEAK = _float_pref("audio_target_peak", 0.75, 0.1, 0.98)
AUDIO_MAX_GAIN = _float_pref("audio_max_gain", 4.0, 1.0, 20.0)
AUDIO_DIAGNOSTIC_SECONDS = _float_pref("audio_diagnostic_seconds", 4.0, 1.0, 15.0)
WHISPER_COMMAND_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_command_vad_filter", False))
WHISPER_CONVERSATION_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_conversation_vad_filter", False))
WHISPER_HOTWORD_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_hotword_vad_filter", True))
WHISPER_COMMAND_BEAM_SIZE = _int_pref("whisper_command_beam_size", 5, 1, 10)
WHISPER_COMMAND_BEST_OF = _int_pref("whisper_command_best_of", 5, 1, 10)
WHISPER_CONVERSATION_BEAM_SIZE = _int_pref("whisper_conversation_beam_size", 3, 1, 10)
WHISPER_CONVERSATION_BEST_OF = _int_pref("whisper_conversation_best_of", 3, 1, 10)
WHISPER_HOTWORD_BEAM_SIZE = _int_pref("whisper_hotword_beam_size", 1, 1, 5)
WHISPER_HOTWORD_BEST_OF = _int_pref("whisper_hotword_best_of", 1, 1, 5)
HOTWORD = str(VOICE_PREFERENCES.get("hotword", "estagiario"))
HOTWORD_LISTENING_ENABLED = bool(VOICE_PREFERENCES.get("hotword_listening_enabled", False))
HOTWORD_TIMEOUT_SECONDS = _float_pref("hotword_timeout_seconds", 3.0, 0.8, 8.0)
HOTWORD_MAX_SILENCE_SECONDS = _float_pref("hotword_max_silence_seconds", 0.5, 0.15, 2.0)
HOTWORD_MIN_SPEECH_SECONDS = _float_pref("hotword_min_speech_seconds", 0.12, 0.05, 1.0)
CONVERSATION_TIMEOUT_SECONDS = _float_pref("conversation_timeout_seconds", 7.0, 1.0, 12.0)
CONVERSATION_MAX_SILENCE_SECONDS = _float_pref("conversation_max_silence_seconds", 1.0, 0.25, 3.0)
CONVERSATION_MIN_SPEECH_SECONDS = _float_pref("conversation_min_speech_seconds", 0.35, 0.08, 2.0)
COMMAND_PROMPT = (
    "Comandos curtos em portugues do Brasil para controlar o computador. "
    "Transcreva sempre em portugues do Brasil, nunca em ingles. "
    "Verbos comuns: abrir, fechar, focar, trocar, minimizar, maximizar, restaurar, pesquisar, ler, selecionar. "
    "Comandos de musica: tocar algo alegre, tocar algo calmo, tocar rock, tocar classico, me surpreenda, "
    "adicionar na fila, tocar musicas curtidas, tocar filho meu, tocar blindado no Spotify. "
    "Alvos comuns: chrome, youtube, google, vscode, code, spotify, whatsapp, zap, bloco de notas, "
    "powershell, edge, github, android studio, steam, mercado livre, magalu."
)
COMMAND_RESCUE_PROMPT = (
    "Transcreva apenas em portugues do Brasil. "
    "Nao invente palavras em ingles. "
    "Priorize comandos curtos e simples. "
    "Exemplos provaveis: o que tem na tela, resuma a tela, detalha a tela, "
    "abrir youtube, abrir chrome, abrir spotify, fechar spotify, "
    "tocar algo alegre, tocar algo calmo, tocar rock, tocar filho meu, tocar blindado no Spotify, me surpreenda, adicionar na fila, "
    "pesquisar notebook no mercado livre, abrir github, abrir whatsapp."
)
CONVERSATION_PROMPT = str(
    VOICE_PREFERENCES.get(
        "conversation_transcription_prompt",
        "Conversa casual em portugues do Brasil.",
    )
).strip()
HOTWORD_PROMPT = f"Palavra de ativacao: {HOTWORD}."
COMMAND_VOCAB = {
    "abre",
    "abrir",
    "abri",
    "abriu",
    "abrei",
    "fecha",
    "fechar",
    "foca",
    "focar",
    "minimiza",
    "maximiza",
    "restaura",
    "pesquisa",
    "pesquisar",
    "procura",
    "procurar",
    "buscar",
    "busca",
    "tela",
    "pagina",
    "janela",
    "resuma",
    "resume",
    "resumir",
    "resumo",
    "detalha",
    "detalhar",
    "explica",
    "github",
    "youtube",
    "spotify",
    "tocar",
    "toque",
    "musica",
    "musicas",
    "alegre",
    "calmo",
    "calma",
    "rock",
    "classico",
    "classica",
    "jazz",
    "gospel",
    "fila",
    "surpreenda",
    "surpreende",
    "filho",
    "meu",
    "blindado",
    "chrome",
    "google",
    "whatsapp",
    "zap",
    "mercado",
    "livre",
    "magalu",
    "bloco",
    "notas",
    "android",
    "studio",
    "vscode",
    "code",
    "edge",
}
ENGLISH_NOISE_TOKENS = {
    "how",
    "did",
    "do",
    "does",
    "you",
    "your",
    "he",
    "she",
    "his",
    "her",
    "me",
    "on",
    "in",
    "the",
    "this",
    "that",
    "whats",
    "what",
    "is",
    "are",
}

_models = {}
_last_key_down = {}
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

VIRTUAL_KEYS = {
    "ESC": 0x1B,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}

HOTKEY_NAME = str(VOICE_PREFERENCES.get("trigger_hotkey", "F8")).upper()
HOTKEY_VK = VIRTUAL_KEYS.get(HOTKEY_NAME, VIRTUAL_KEYS["F8"])
TOGGLE_LISTENING_HOTKEY_NAME = str(VOICE_PREFERENCES.get("toggle_listening_hotkey", "F9")).upper()
TOGGLE_LISTENING_HOTKEY_VK = VIRTUAL_KEYS.get(TOGGLE_LISTENING_HOTKEY_NAME, VIRTUAL_KEYS["F9"])
SPEECH_INTERRUPT_KEYS = {
    HOTKEY_VK,
    TOGGLE_LISTENING_HOTKEY_VK,
    VIRTUAL_KEYS["ESC"],
}


@dataclass
class VoiceResult:
    ok: bool
    text: str = ""
    error: str = ""
    command_text: str = ""


def _run_powershell(script: str, timeout_seconds: int = 20) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.run(
        [
            POWERSHELL_EXE,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def _model_repo(model_size: str) -> str:
    return f"Systran/faster-whisper-{model_size}"


def _get_model(model_size: str) -> WhisperModel:
    model = _models.get(model_size)
    if model is not None:
        return model

    repo = _model_repo(model_size)
    try:
        model_path = snapshot_download(repo, local_files_only=True)
    except LocalEntryNotFoundError:
        model_path = snapshot_download(repo, local_files_only=False)

    model = WhisperModel(model_path, device="cpu", compute_type="int8")
    _models[model_size] = model
    return model


def _chunk_levels(chunk: np.ndarray) -> tuple[float, float]:
    if not chunk.size:
        return 0.0, 0.0

    peak = float(np.max(np.abs(chunk)))
    rms = float(np.sqrt(np.mean(np.square(chunk))))
    return peak, rms


def _chunk_has_speech(chunk: np.ndarray, threshold: float) -> bool:
    peak, rms = _chunk_levels(chunk)
    return peak >= threshold or rms >= threshold * 0.35


def _normalized_device_name(text: str) -> str:
    return _normalize_recognized_text(text or "")


def list_input_devices() -> list[dict]:
    try:
        devices = sd.query_devices()
    except Exception:
        return []

    default_input = None
    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = None

    rows = []
    for index, device in enumerate(devices):
        try:
            max_inputs = int(device.get("max_input_channels", 0) or 0)
        except Exception:
            max_inputs = 0
        if max_inputs <= 0:
            continue

        rows.append(
            {
                "index": index,
                "name": str(device.get("name", f"Dispositivo {index}")).strip(),
                "channels": max_inputs,
                "default_samplerate": int(device.get("default_samplerate", SAMPLE_RATE) or SAMPLE_RATE),
                "is_default": default_input == index,
            }
        )

    return rows


def _resolve_input_device() -> tuple[int | None, dict | None]:
    devices = list_input_devices()
    if not devices:
        return None, None

    preferences = load_voice_preferences()
    preferred_name = _normalized_device_name(str(preferences.get("audio_input_device", "")).strip())

    if preferred_name:
        exact_match = next(
            (device for device in devices if _normalized_device_name(device["name"]) == preferred_name),
            None,
        )
        if exact_match:
            return int(exact_match["index"]), exact_match

        contains_match = next(
            (device for device in devices if preferred_name in _normalized_device_name(device["name"])),
            None,
        )
        if contains_match:
            return int(contains_match["index"]), contains_match

        best_match = None
        best_score = 0.0
        for device in devices:
            score = difflib.SequenceMatcher(
                None,
                preferred_name,
                _normalized_device_name(device["name"]),
            ).ratio()
            if score > best_score:
                best_score = score
                best_match = device
        if best_match and best_score >= 0.62:
            return int(best_match["index"]), best_match

    default_device = next((device for device in devices if device.get("is_default")), None)
    if default_device:
        return int(default_device["index"]), default_device

    return int(devices[0]["index"]), devices[0]


def get_active_input_device_info() -> dict | None:
    _index, device = _resolve_input_device()
    return device


def format_input_devices() -> str:
    devices = list_input_devices()
    if not devices:
        return "Não encontrei microfones disponíveis."

    active = get_active_input_device_info()
    rows = []
    for device in devices[:12]:
        label = device["name"]
        tags = []
        if device.get("is_default"):
            tags.append("padrão do Windows")
        if active and device["index"] == active["index"]:
            tags.append("em uso pelo assistente")
        if tags:
            label += " (" + ", ".join(tags) + ")"
        rows.append(f"{device['index']}. {label}")

    return "Microfones disponíveis: " + "; ".join(rows) + "."


def _preprocess_audio(audio: np.ndarray) -> np.ndarray:
    if audio.size == 0:
        return audio

    processed = audio.astype(np.float32, copy=True)

    if AUDIO_DC_OFFSET_FILTER:
        processed -= float(np.mean(processed))

    peak, _rms = _chunk_levels(processed)

    if AUDIO_NORMALIZE_ENABLED and peak > 0.0001:
        gain = min(AUDIO_MAX_GAIN, AUDIO_TARGET_PEAK / peak)
        processed *= gain

    return np.clip(processed, -1.0, 1.0)


def _record_audio(
    timeout_seconds: float,
    min_speech_seconds: float = DEFAULT_MIN_SPEECH_SECONDS,
    max_silence_seconds: float = DEFAULT_MAX_SILENCE_SECONDS,
) -> np.ndarray:
    input_device, _device_info = _resolve_input_device()
    chunks = []
    preroll_chunks = deque(maxlen=max(1, int((SAMPLE_RATE * AUDIO_PREROLL_SECONDS) / FRAME_SIZE)))
    speech_detected = False
    speech_frames = 0
    silence_after_speech_frames = 0
    noise_floor = 0.0
    effective_threshold = SILENCE_THRESHOLD
    max_frames = int(SAMPLE_RATE * min(float(timeout_seconds), DEFAULT_MAX_RECORD_SECONDS))

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=FRAME_SIZE,
    ) as stream:
        collected_frames = 0

        while collected_frames < max_frames:
            chunk, _overflowed = stream.read(FRAME_SIZE)
            chunk = chunk.reshape(-1)
            collected_frames += len(chunk)

            peak, _rms = _chunk_levels(chunk)
            has_speech = _chunk_has_speech(chunk, effective_threshold)

            if not speech_detected and not has_speech:
                preroll_chunks.append(chunk)

                if AUDIO_DYNAMIC_THRESHOLD:
                    noise_floor = (noise_floor * 0.85) + (peak * 0.15)
                    effective_threshold = min(
                        AUDIO_MAX_DYNAMIC_THRESHOLD,
                        max(SILENCE_THRESHOLD, noise_floor * AUDIO_NOISE_MULTIPLIER),
                    )
                continue

            if has_speech:
                if not speech_detected:
                    chunks.extend(preroll_chunks)
                    preroll_chunks.clear()
                speech_detected = True
                speech_frames += len(chunk)
                silence_after_speech_frames = 0
                chunks.append(chunk)
            elif speech_detected:
                silence_after_speech_frames += len(chunk)
                chunks.append(chunk)

            enough_speech = speech_frames >= int(SAMPLE_RATE * min_speech_seconds)
            enough_silence = silence_after_speech_frames >= int(SAMPLE_RATE * max_silence_seconds)

            if speech_detected and enough_speech and enough_silence:
                break

    if not chunks:
        if not preroll_chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(list(preroll_chunks))

    return np.concatenate(chunks)


def _record_fixed_audio(duration_seconds: float) -> np.ndarray:
    input_device, _device_info = _resolve_input_device()
    chunks = []
    total_frames = int(SAMPLE_RATE * duration_seconds)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=FRAME_SIZE,
    ) as stream:
        collected_frames = 0
        while collected_frames < total_frames:
            chunk, _overflowed = stream.read(min(FRAME_SIZE, total_frames - collected_frames))
            chunk = chunk.reshape(-1)
            chunks.append(chunk)
            collected_frames += len(chunk)

    if not chunks:
        return np.array([], dtype=np.float32)

    return np.concatenate(chunks)


def _audio_has_signal(audio: np.ndarray) -> bool:
    if audio.size == 0:
        return False

    return _chunk_has_speech(audio, SILENCE_THRESHOLD)


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _normalize_recognized_text(text: str) -> str:
    normalized = _strip_accents(text.lower().strip())
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _command_token_similarity(token: str) -> float:
    if not token:
        return 0.0
    return max((difflib.SequenceMatcher(None, token, candidate).ratio() for candidate in COMMAND_VOCAB), default=0.0)


def _command_transcription_score(text: str) -> float:
    normalized = _normalize_recognized_text(text)
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return 0.0

    score = 0.0
    for token in tokens:
        similarity = _command_token_similarity(token)
        if similarity >= 0.9:
            score += 2.2
        elif similarity >= 0.78:
            score += 1.2
        elif similarity >= 0.68:
            score += 0.5

        if token in ENGLISH_NOISE_TOKENS:
            score -= 1.4

    if any(token in {"tela", "pagina", "youtube", "github", "spotify", "chrome"} for token in tokens):
        score += 0.8

    return score / max(1, len(tokens))


def _should_retry_command_transcription(text: str) -> bool:
    normalized = _normalize_recognized_text(text)
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return False

    if len(tokens) == 1 and _command_token_similarity(tokens[0]) >= 0.84:
        return False

    score = _command_transcription_score(text)
    english_hits = sum(1 for token in tokens if token in ENGLISH_NOISE_TOKENS)

    if english_hits >= 1 and score < 0.45:
        return True

    if len(tokens) <= 5 and score < 0.28:
        return True

    return False


def _is_prompt_hallucination(text: str) -> bool:
    normalized = _normalize_recognized_text(text)
    if not normalized:
        return False

    prompt_fragments = {
        "comandos curtos em portugues do brasil",
        "comandos em portugues do brasil",
        "comandos em português do brasil",
        "legendas pela comunidade de amara org",
        "legendas pela comunidade amara org",
        "amara org",
        "transcreva sempre em portugues do brasil",
        "conversa casual em portugues do brasil",
        "verbos comuns abrir fechar focar trocar minimizar maximizar restaurar pesquisar ler selecionar",
    }
    if normalized in prompt_fragments:
        return True

    return any(fragment in normalized for fragment in prompt_fragments)


def _extract_inline_command(text: str, hotword: str) -> str:
    hotword_normalized = _normalize_recognized_text(hotword)
    normalized_text = _normalize_recognized_text(text)

    if not normalized_text or not hotword_normalized:
        return ""

    if normalized_text == hotword_normalized:
        return ""

    original_tokens = text.strip().split()
    normalized_tokens = [_normalize_recognized_text(token) for token in original_tokens]
    hotword_tokens = hotword_normalized.split()
    hotword_token_count = len(hotword_tokens)

    for start in range(0, len(normalized_tokens) - hotword_token_count + 1):
        window = normalized_tokens[start:start + hotword_token_count]
        if window == hotword_tokens:
            command_tokens = original_tokens[start + hotword_token_count:]
            return " ".join(command_tokens).strip(" ,.!?:;")

        candidate = " ".join(window).strip()
        if difflib.SequenceMatcher(None, candidate, hotword_normalized).ratio() >= 0.74:
            command_tokens = original_tokens[start + hotword_token_count:]
            return " ".join(command_tokens).strip(" ,.!?:;")

    if normalized_text.startswith(hotword_normalized + " "):
        return text[len(text.split()[0]):].strip(" ,.!?:;")

    return ""


def _save_temp_wav(audio: np.ndarray) -> str:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp.close()
    _save_wav(temp.name, audio)
    return temp.name


def _save_wav(path: str | Path, audio: np.ndarray):
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    write_wav(str(path), SAMPLE_RATE, pcm)


def _format_audio_stats(label: str, audio: np.ndarray) -> str:
    peak, rms = _chunk_levels(audio)
    duration = audio.size / SAMPLE_RATE if audio.size else 0.0
    return f"{label}: duracao={duration:.2f}s pico={peak:.4f} rms={rms:.4f}"


def run_audio_diagnostic(seconds: float | None = None) -> str:
    duration = seconds if seconds is not None else AUDIO_DIAGNOSTIC_SECONDS
    duration = max(1.0, min(15.0, float(duration)))
    active_device = get_active_input_device_info()

    try:
        raw_audio = _record_fixed_audio(duration)
    except Exception as exc:
        return f"Falha ao gravar diagnostico de audio: {exc}"

    processed_audio = _preprocess_audio(raw_audio)
    output_dir = Path("memory") / "audio_diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"audio_raw_{stamp}.wav"
    processed_path = output_dir / f"audio_processed_{stamp}.wav"

    _save_wav(raw_path, raw_audio)
    _save_wav(processed_path, processed_audio)
    raw_transcription = _transcribe_audio(
        raw_audio,
        model_size=COMMAND_MODEL_SIZE,
        prompt=COMMAND_PROMPT,
        beam_size=WHISPER_COMMAND_BEAM_SIZE,
        best_of=WHISPER_COMMAND_BEST_OF,
        vad_filter=WHISPER_COMMAND_VAD_FILTER,
        preprocess=False,
    )
    processed_transcription = _transcribe_audio(
        processed_audio,
        model_size=COMMAND_MODEL_SIZE,
        prompt=COMMAND_PROMPT,
        beam_size=WHISPER_COMMAND_BEAM_SIZE,
        best_of=WHISPER_COMMAND_BEST_OF,
        vad_filter=WHISPER_COMMAND_VAD_FILTER,
        preprocess=False,
    )
    raw_text = raw_transcription.text if raw_transcription.ok else raw_transcription.error
    processed_text = processed_transcription.text if processed_transcription.ok else processed_transcription.error

    return "\n".join(
        [
            "Diagnostico de audio concluido.",
            (
                f"Microfone usado: {active_device['name']}"
                if active_device
                else "Microfone usado: padrão do Windows"
            ),
            _format_audio_stats("Bruto", raw_audio),
            _format_audio_stats("Processado", processed_audio),
            f"Whisper bruto: {raw_text}",
            f"Whisper processado: {processed_text}",
            f"Arquivo bruto: {raw_path.resolve()}",
            f"Arquivo processado: {processed_path.resolve()}",
        ]
    )


def _transcribe_audio(
    audio: np.ndarray,
    model_size: str,
    prompt: str | None,
    beam_size: int,
    best_of: int,
    vad_filter: bool,
    preprocess: bool = True,
) -> VoiceResult:
    if not _audio_has_signal(audio):
        return VoiceResult(ok=False, error="Nao detectei fala no microfone.")

    def _transcribe_once(active_prompt: str | None, active_beam: int, active_best_of: int, active_vad: bool):
        processed_audio = _preprocess_audio(audio) if preprocess else audio
        active_temp_path = _save_temp_wav(processed_audio)
        try:
            model = _get_model(model_size)
            segments, info = model.transcribe(
                active_temp_path,
                language="pt",
                task="transcribe",
                vad_filter=active_vad,
                beam_size=active_beam,
                best_of=active_best_of,
                temperature=0.0,
                initial_prompt=active_prompt or None,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return text, info
        finally:
            if active_temp_path and os.path.exists(active_temp_path):
                os.remove(active_temp_path)

    temp_path = None
    try:
        text, info = _transcribe_once(prompt, beam_size, best_of, vad_filter)

        if not text:
            return VoiceResult(ok=False, error="Nenhuma fala reconhecida.")

        if model_size == COMMAND_MODEL_SIZE and _is_prompt_hallucination(text):
            rescue_text, _rescue_info = _transcribe_once(
                None,
                max(beam_size, 6),
                max(best_of, 6),
                False,
            )
            if rescue_text and not _is_prompt_hallucination(rescue_text):
                text = rescue_text
            else:
                return VoiceResult(ok=False, error="Não captei com precisão.")

        if (
            model_size == COMMAND_MODEL_SIZE
            and prompt == COMMAND_PROMPT
            and _should_retry_command_transcription(text)
        ):
            rescue_text, _rescue_info = _transcribe_once(
                COMMAND_RESCUE_PROMPT,
                max(beam_size, 6),
                max(best_of, 6),
                False,
            )
            if rescue_text and _command_transcription_score(rescue_text) > _command_transcription_score(text):
                text = rescue_text

        if info.language_probability is not None and info.language_probability < 0.25:
            return VoiceResult(ok=True, text=text)

        return VoiceResult(ok=True, text=text)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao transcrever audio: {exc}")


def _contains_hotword(text: str, hotword: str) -> bool:
    normalized_text = text.lower().strip()
    if hotword in normalized_text:
        return True

    for token in normalized_text.replace(",", " ").replace(".", " ").split():
        if difflib.SequenceMatcher(None, token, hotword).ratio() >= 0.72:
            return True

    if difflib.SequenceMatcher(None, normalized_text, hotword).ratio() >= 0.62:
        return True

    return False


def _consume_key_press(vk_code: int) -> bool:
    was_down = _last_key_down.get(vk_code, False)
    is_down = bool(user32.GetAsyncKeyState(vk_code) & 0x8000)
    pressed_now = is_down and not was_down
    _last_key_down[vk_code] = is_down
    return pressed_now


def consume_hotkey_press() -> bool:
    return _consume_key_press(HOTKEY_VK)


def consume_toggle_listening_hotkey_press() -> bool:
    return _consume_key_press(TOGGLE_LISTENING_HOTKEY_VK)


def speech_interrupt_pressed() -> bool:
    return any(_consume_key_press(vk_code) for vk_code in SPEECH_INTERRUPT_KEYS)


def play_activation_sound():
    if not bool(VOICE_PREFERENCES.get("activation_sound", True)):
        return

    try:
        hz = int(VOICE_PREFERENCES.get("activation_sound_hz", 880))
        duration = int(VOICE_PREFERENCES.get("activation_sound_ms", 120))
        winsound.Beep(hz, duration)
    except Exception:
        try:
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def _float_setting(name: str, default: float) -> str:
    try:
        return str(float(VOICE_PREFERENCES.get(name, default)))
    except (TypeError, ValueError):
        return str(default)


def _load_tts_pronunciations() -> dict[str, str]:
    if not bool(VOICE_PREFERENCES.get("tts_pronunciations_enabled", True)):
        return {}

    try:
        data = json.loads(TTS_PRONUNCIATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        str(source): str(target)
        for source, target in data.items()
        if str(source).strip() and str(target).strip()
    }


_NUMBER_WORDS = {
    0: "zero",
    1: "um",
    2: "dois",
    3: "três",
    4: "quatro",
    5: "cinco",
    6: "seis",
    7: "sete",
    8: "oito",
    9: "nove",
    10: "dez",
    11: "onze",
    12: "doze",
    13: "treze",
    14: "quatorze",
    15: "quinze",
    16: "dezesseis",
    17: "dezessete",
    18: "dezoito",
    19: "dezenove",
    20: "vinte",
    30: "trinta",
    40: "quarenta",
    50: "cinquenta",
    60: "sessenta",
    70: "setenta",
    80: "oitenta",
    90: "noventa",
    100: "cem",
}

_HUNDRED_WORDS = {
    100: "cento",
    200: "duzentos",
    300: "trezentos",
    400: "quatrocentos",
    500: "quinhentos",
    600: "seiscentos",
    700: "setecentos",
    800: "oitocentos",
    900: "novecentos",
}

_MONTH_NAMES_PTBR = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

_SPELLED_LETTER_NAMES = {
    "A": "á",
    "B": "bê",
    "C": "cê",
    "D": "dê",
    "E": "ê",
    "F": "éfe",
    "G": "gê",
    "H": "agá",
    "I": "i",
    "J": "jóta",
    "K": "cá",
    "L": "éle",
    "M": "ême",
    "N": "êne",
    "O": "ó",
    "P": "pê",
    "Q": "quê",
    "R": "érre",
    "S": "ésse",
    "T": "tê",
    "U": "u",
    "V": "vê",
    "W": "dáblio",
    "X": "xis",
    "Y": "ípsilon",
    "Z": "zê",
}

_TTS_ABBREVIATION_RULES = {
    "mAh": {"mode": "expand", "value": "miliampere hora"},
    "MAh": {"mode": "expand", "value": "miliampere hora"},
    "mah": {"mode": "expand", "value": "miliampere hora"},
    "Wh": {"mode": "expand", "value": "watt hora"},
    "kWh": {"mode": "expand", "value": "quilo watt hora"},
    "km": {"mode": "expand", "value": "quilômetro"},
    "kg": {"mode": "expand", "value": "quilo"},
    "MB": {"mode": "expand", "value": "megabyte"},
    "mb": {"mode": "expand", "value": "megabyte"},
    "GB": {"mode": "expand", "value": "gigabyte"},
    "gb": {"mode": "expand", "value": "gigabyte"},
    "TB": {"mode": "expand", "value": "terabyte"},
    "tb": {"mode": "expand", "value": "terabyte"},
    "RAM": {"mode": "spell"},
    "CPU": {"mode": "spell"},
    "GPU": {"mode": "spell"},
    "USB": {"mode": "spell"},
    "NFC": {"mode": "spell"},
    "SSD": {"mode": "spell"},
    "HD": {"mode": "spell"},
    "LED": {"mode": "spell"},
    "LCD": {"mode": "spell"},
    "LLM": {"mode": "spell"},
    "IA": {"mode": "spell"},
    "AI": {"mode": "spell"},
    "API": {"mode": "spell"},
    "OCR": {"mode": "spell"},
    "RPA": {"mode": "spell"},
    "UI": {"mode": "spell"},
    "UX": {"mode": "spell"},
    "PDF": {"mode": "spell"},
    "JSON": {"mode": "spell"},
    "URL": {"mode": "spell"},
    "HTTP": {"mode": "spell"},
    "HTTPS": {"mode": "spell"},
    "HDMI": {"mode": "spell"},
    "RGB": {"mode": "spell"},
    "NASA": {"mode": "word"},
    "laser": {"mode": "word"},
    "Laser": {"mode": "word"},
}

_PRONOUNCE_AS_WORD = {
    "NASA",
    "LASER",
    "RADAR",
    "WiFi",
    "WIFI",
}

_BUILTIN_TTS_PRONUNCIATIONS = {
    "GitHub": "guíti rãb",
    "github": "guíti rãb",
    "YouTube": "iútubi",
    "youtube": "iútubi",
    "Steam": "stim",
    "steam": "stim",
    "Chrome": "crôum",
    "chrome": "crôum",
    "Python": "paithon",
    "python": "paithon",
    "Google": "gúgou",
    "google": "gúgou",
    "Colab": "cólab",
    "colab": "cólab",
    "Android": "êndróid",
    "android": "êndróid",
    "Android Studio": "êndróid stúdio",
    "android studio": "êndróid stúdio",
    "PowerShell": "páuer shel",
    "powershell": "páuer shel",
    "OpenAI": "ôupen êi ái",
    "openai": "ôupen êi ái",
    "Wi-Fi": "uái fai",
    "wi-fi": "uái fai",
    "Wi Fi": "uái fai",
    "wi fi": "uái fai",
    "WiFi": "uái fai",
    "wifi": "uái fai",
    "Bluetooth": "blutúfi",
    "bluetooth": "blutúfi",
    "Mercado Livre": "mercádo lívre",
    "mercado livre": "mercádo lívre",
    "Magalu": "magalú",
    "magalu": "magalú",
    "Spotify": "ispótifai",
    "spotify": "ispótifai",
    "VS Code": "vê ésse côde",
    "VSCode": "vê ésse côde",
    "vscode": "vê ésse côde",
    "Whisper": "uísper",
    "whisper": "uísper",
    "Piper": "paiper",
    "piper": "paiper",
    "Ollama": "olâma",
    "ollama": "olâma",
    "Mobile": "môbail",
    "mobile": "môbail",
    "screenpilot": "screen pilot",
    "ScreenPilot": "screen pilot",
}


def _number_to_pt(value: int, feminine_one: bool = False) -> str:
    if feminine_one and value == 1:
        return "uma"

    if value in _NUMBER_WORDS:
        return _NUMBER_WORDS[value]

    if value < 100:
        ten = (value // 10) * 10
        unit = value % 10
        return f"{_NUMBER_WORDS[ten]} e {_number_to_pt(unit, feminine_one=feminine_one)}"

    if value < 1000:
        hundred = (value // 100) * 100
        rest = value % 100
        if rest == 0:
            return _HUNDRED_WORDS.get(hundred, str(value))
        return f"{_HUNDRED_WORDS.get(hundred, str(hundred))} e {_number_to_pt(rest, feminine_one=feminine_one)}"

    if value < 1_000_000:
        thousands = value // 1000
        rest = value % 1000

        if thousands == 1:
            prefix = "mil"
        else:
            prefix = f"{_number_to_pt(thousands, feminine_one=feminine_one)} mil"

        if rest == 0:
            return prefix

        connector = " e " if rest < 100 else ", "
        return f"{prefix}{connector}{_number_to_pt(rest, feminine_one=feminine_one)}"

    return str(value)


def _expand_time_expression(match: re.Match) -> str:
    hour = int(match.group(1))
    minute = match.group(2) if len(match.groups()) >= 2 else None
    hour_word = _number_to_pt(hour, feminine_one=True)

    if minute is None:
        unit = "hora" if hour == 1 else "horas"
        return f"{hour_word} {unit}"

    minute_value = int(minute)
    minute_word = _number_to_pt(minute_value, feminine_one=True)
    minute_unit = "minuto" if minute_value == 1 else "minutos"
    return f"{hour_word} horas e {minute_word} {minute_unit}"


def _expand_date_expression(match: re.Match) -> str:
    try:
        day = int(match.group(1))
        month = int(match.group(2))
    except (TypeError, ValueError):
        return match.group(0)

    if day < 1 or day > 31 or month not in _MONTH_NAMES_PTBR:
        return match.group(0)

    day_text = "primeiro" if day == 1 else _number_to_pt(day)
    year = match.group(3)
    year_text = ""
    if year:
        year_value = int(year)
        if year_value < 100:
            year_value += 2000 if year_value < 50 else 1900
        year_text = f" de {_number_to_pt(year_value)}"

    return f"{day_text} de {_MONTH_NAMES_PTBR[month]}{year_text}"


def _expand_temperature_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = "grau" if value == 1 else "graus"
    return f"{_number_to_pt(value)} {unit} Célsius"


def _expand_degrees_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = "grau" if value == 1 else "graus"
    return f"{_number_to_pt(value)} {unit}"


def _expand_storage_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = (match.group(2) or "").upper()

    if unit == "MB":
        unit_text = "megabyte" if value == 1 else "megabytes"
    elif unit == "GB":
        unit_text = "gigabyte" if value == 1 else "gigabytes"
    elif unit == "TB":
        unit_text = "terabyte" if value == 1 else "terabytes"
    else:
        return match.group(0)

    return f"{_number_to_pt(value)} {unit_text}"


def _spell_acronym(token: str) -> str:
    parts = []
    for char in token:
        parts.append(_SPELLED_LETTER_NAMES.get(char.upper(), char.lower()))
    return " ".join(parts)


def _looks_pronounceable_acronym(token: str) -> bool:
    upper = token.upper()
    if upper in _PRONOUNCE_AS_WORD:
        return True

    if len(token) < 3 or len(token) > 5:
        return False

    vowels = sum(1 for char in upper if char in "AEIOU")
    consonants = sum(1 for char in upper if "A" <= char <= "Z" and char not in "AEIOU")
    return vowels >= 2 and consonants >= 1


def _apply_abbreviation_rules(text: str) -> str:
    for source, rule in _TTS_ABBREVIATION_RULES.items():
        mode = str(rule.get("mode", "")).strip().lower()
        if mode == "expand":
            replacement = str(rule.get("value", "")).strip()
        elif mode == "spell":
            replacement = _spell_acronym(source)
        elif mode == "word":
            replacement = source.lower()
        else:
            continue

        if replacement:
            text = re.sub(rf"\b{re.escape(source)}\b", replacement, text)

    return text


def _apply_abbreviation_heuristics(text: str) -> str:
    def replacer(match: re.Match) -> str:
        token = match.group(0)
        if token in _TTS_ABBREVIATION_RULES:
            return token

        if any(char.islower() for char in token) and any(char.isupper() for char in token):
            lower = token.lower()
            if lower.endswith("mah"):
                return "miliampere hora"
            if lower.endswith("kwh"):
                return "quilo watt hora"
            if lower.endswith("wh"):
                return "watt hora"
            return token

        if token.isupper() and len(token) <= 4:
            if _looks_pronounceable_acronym(token):
                return token.lower()
            return _spell_acronym(token)

        return token

    return re.sub(r"\b[A-Za-zÀ-ÿ]{2,5}\b", replacer, text)


def _replace_quoted_segment(match: re.Match) -> str:
    content = re.sub(r"\s+", " ", match.group(1) or "").strip(" ,")
    if not content:
        return ""
    return f", {content}, "


def _normalize_tts_tech_terms(text: str) -> str:
    replacements = {
        r"\bWi[\-\s]?Fi\b": "WiFi",
        r"\bwi[\-\s]?fi\b": "wifi",
        r"\bVS[\-\s]?Code\b": "VS Code",
        r"\bvs[\-\s]?code\b": "vscode",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text


def _normalize_tts_quotes_and_brackets(text: str) -> str:
    text = re.sub(r'(?<!\w)"([^"\n]{1,120})"(?!\w)', _replace_quoted_segment, text)
    text = re.sub(r"(?<!\w)'([^'\n]{1,120})'(?!\w)", _replace_quoted_segment, text)
    text = re.sub(r"\(([^()\n]{1,120})\)", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    text = re.sub(r"\[([^\[\]\n]{1,120})\]", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    text = re.sub(r"\{([^\{\}\n]{1,120})\}", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    return text


def _capitalize_tts_sentences(text: str) -> str:
    def replacer(match: re.Match) -> str:
        prefix = match.group(1)
        letter = match.group(2)
        return f"{prefix}{letter.upper()}"

    text = re.sub(r"(^|[.!?]\s+)([a-zà-ÿ])", replacer, text)
    return text


def _normalize_tts_punctuation(text: str) -> str:
    ellipsis_token = " __TTS_ELLIPSIS__ "
    sentence_break = "\n"
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    text = _normalize_tts_quotes_and_brackets(text)
    text = re.sub(r"\s*(?:\.{3,}|\u2026)\s*", ellipsis_token, text)
    text = re.sub(r"\s*[–—-]\s*", ", ", text)
    text = re.sub(r"\s*/\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:])(?=\S)", r"\1 ", text)
    text = re.sub(r"([!?]){2,}", r"\1", text)
    text = re.sub(r"(\.){4,}", "...", text)

    text = re.sub(r"\s*;\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*:\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*\.\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*\?\s*", f"?{sentence_break}", text)
    text = re.sub(r"\s*!\s*", f"!{sentence_break}", text)
    text = text.replace(ellipsis_token.strip(), f"...{sentence_break}")
    text = re.sub(r"\s*\.\.\.\s*", f"...{sentence_break}", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r",\s*\.", f".{sentence_break}", text)
    text = re.sub(r"\.\s*,", f".{sentence_break}", text)
    text = re.sub(r",\s*([!?])", rf"\1{sentence_break}", text)
    text = re.sub(rf"{sentence_break}{{2,}}", sentence_break, text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(rf"[ \t]*{sentence_break}[ \t]*", sentence_break, text)
    text = text.strip()
    return _capitalize_tts_sentences(text)


def _expand_tts_reading_patterns(text: str) -> str:
    text = re.sub(r"\b([01]?\d|2[0-3])h([0-5]\d)\b", _expand_time_expression, text)
    text = re.sub(r"\b([01]?\d|2[0-3])h\b", _expand_time_expression, text)
    text = re.sub(
        r"\b(\d{1,3})\s*(?:°\s*C|graus?\s+Celsius|graus?\s+celsius)\b",
        _expand_temperature_expression,
        text,
    )
    text = re.sub(r"\b(\d{1,3})\s+graus\b", _expand_degrees_expression, text)
    text = re.sub(r"\b(\d{1,5})\s*mAh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} miliampere hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*Wh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*kWh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilo watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*(MB|GB|TB)\b", _expand_storage_expression, text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,4})\s*km\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilômetros", text, flags=re.IGNORECASE)
    return text


def _expand_negative_tts_patterns(text: str) -> str:
    text = re.sub(r"(?<!\w)-\s*(R\$\s*\d[\d\.,]*)", r"menos \1", text)

    def percent_replacer(match: re.Match) -> str:
        number = str(match.group(1) or "").strip()
        if "," in number:
            integer, decimal = number.split(",", 1)
            if decimal:
                return f"menos {integer} vírgula {decimal} por cento"
        if "." in number:
            integer, decimal = number.split(".", 1)
            if decimal:
                return f"menos {integer} ponto {decimal} por cento"
        return f"menos {number} por cento"

    text = re.sub(r"(?<!\w)-\s*(\d[\d\.,]*)\s*%", percent_replacer, text)
    return text


def _normalize_numeric_token_for_tts(number: str) -> str:
    token = str(number or "").strip()
    if not token:
        return token
    if "," in token:
        token = token.replace(".", "")
        integer, decimal = token.split(",", 1)
        return f"{integer} vírgula {decimal}"
    if "." in token:
        integer, decimal = token.split(".", 1)
        return f"{integer} ponto {decimal}"
    return token


def _expand_currency_tts_patterns(text: str) -> str:
    def scaled_currency_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        scale = str(match.group(2) or "").strip()
        return f"{number} {scale} de reais"

    text = re.sub(
        r"R\$\s*([-+]?\d+(?:[.,]\d+)?)\s*((?:bilh|milh)\w+|mil)\b",
        scaled_currency_replacer,
        text,
        flags=re.IGNORECASE,
    )

    def currency_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        return f"{number} reais"

    return re.sub(r"R\$\s*([-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)", currency_replacer, text, flags=re.IGNORECASE)


def _expand_percent_tts_patterns(text: str) -> str:
    def percent_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        return f"{number} por cento"

    return re.sub(r"(?<![\w-])(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+\.\d+)\s*%", percent_replacer, text)


def _expand_general_decimal_tts_patterns(text: str) -> str:
    def number_replacer(match: re.Match) -> str:
        token = match.group(1)
        return _normalize_numeric_token_for_tts(token)

    return re.sub(r"(?<![\w])(\d{1,3}(?:\.\d{3})*(?:,\d+)|\d+\.\d+)(?![\w%])", number_replacer, text)


def _expand_ticker_for_tts(text: str) -> str:
    letter_map = {
        "A": "á",
        "B": "bê",
        "C": "cê",
        "D": "dê",
        "E": "é",
        "F": "éfe",
        "G": "gê",
        "H": "agá",
        "I": "i",
        "J": "jóta",
        "K": "cá",
        "L": "éle",
        "M": "ême",
        "N": "êne",
        "O": "ó",
        "P": "pê",
        "Q": "quê",
        "R": "erre",
        "S": "ésse",
        "T": "tê",
        "U": "u",
        "V": "vê",
        "W": "dáblio",
        "X": "xis",
        "Y": "ípsilon",
        "Z": "zê",
    }

    def replacer(match: re.Match) -> str:
        letters = match.group(1).upper()
        digits = match.group(2)
        spoken_letters = " ".join(letter_map.get(letter, letter.lower()) for letter in letters)
        spoken_digits = " ".join(_number_to_pt(int(digit)) for digit in digits)
        return f"{spoken_letters} {spoken_digits}".strip()

    return re.sub(r"\b([A-Z]{4})(\d{1,2})\b", replacer, text)


def _restore_common_ptbr_accents(text: str) -> str:
    replacements = {
        "pagina": "página",
        "paginas": "páginas",
        "visao": "visão",
        "acoes": "ações",
        "acao": "ação",
        "rapida": "rápida",
        "rapido": "rápido",
        "repositorio": "repositório",
        "repositorios": "repositórios",
        "conteudo": "conteúdo",
        "conteudos": "conteúdos",
        "inteligencia": "inteligência",
        "computacao": "computação",
        "automacao": "automação",
        "camera": "câmera",
        "cameras": "câmeras",
        "videoaula": "vídeoaula",
        "musica": "música",
        "musicas": "músicas",
        "video": "vídeo",
        "videos": "vídeos",
        "audio": "áudio",
        "audios": "áudios",
        "traducao": "tradução",
        "informacao": "informação",
        "informacoes": "informações",
        "selecao": "seleção",
        "selecoes": "seleções",
        "opcao": "opção",
        "opcoes": "opções",
        "proxima": "próxima",
        "proximo": "próximo",
        "numero": "número",
        "numeros": "números",
        "navegacao": "navegação",
        "sintese": "síntese",
        "configuracao": "configuração",
        "configuracoes": "configurações",
        "precisao": "precisão",
        "ingles": "inglês",
        "classificacao": "classificação",
        "explicacao": "explicação",
        "nao": "não",
        "voce": "você",
        "voces": "vocês",
        "util": "útil",
        "uteis": "úteis",
        "alem": "além",
        "comecar": "começar",
        "comeco": "começo",
        "comeca": "começa",
        "comecou": "começou",
        "disposicao": "disposição",
        "instrucao": "instrução",
        "instrucoes": "instruções",
        "patrimonio": "patrimônio",
        "politica": "política",
        "politicas": "políticas",
        "cambio": "câmbio",
        "criterios": "critérios",
        "preferencia": "preferência",
        "preferencias": "preferências",
        "cotacoes": "cotações",
        "relatorio": "relatório",
        "relatorios": "relatórios",
        "especifico": "específico",
        "especifica": "específica",
    }

    replacements.update(
        {
            "avaliacao": "avaliação",
            "comparacao": "comparação",
            "comparacoes": "comparações",
            "variacao": "variação",
            "variacoes": "variações",
            "cotacao": "cotação",
            "cotacoes": "cotações",
            "geracao": "geração",
            "evolucao": "evolução",
            "operacao": "operação",
            "operacoes": "operações",
            "direcao": "direção",
            "funcao": "função",
            "funcoes": "funções",
            "atencao": "atenção",
            "situacao": "situação",
            "condicao": "condição",
            "condicoes": "condições",
            "criterio": "critério",
            "memoria": "memória",
            "historico": "histórico",
            "analise": "análise",
            "tecnico": "técnico",
            "tecnica": "técnica",
            "tecnicas": "técnicas",
            "pratico": "prático",
            "pratica": "prática",
            "estrategia": "estratégia",
            "estrategias": "estratégias",
            "logica": "lógica",
            "topico": "tópico",
            "topicos": "tópicos",
            "critico": "crítico",
            "critica": "crítica",
            "projecao": "projeção",
            "projecoes": "projeções",
        }
    )

    for source, target in replacements.items():
        text = re.sub(rf"\b{source}\b", target, text, flags=re.IGNORECASE)

    return text


def _apply_pronunciation_map(text: str, mapping: dict[str, str]) -> str:
    ordered_items = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    for source, target in ordered_items:
        text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return text


def _massage_ptbr_pronunciation(text: str) -> str:
    phrase_replacements = {
        "Pronto para trabalhar.": "Pronto para começar.",
        "pronto para trabalhar.": "pronto para começar.",
        "Vamos fazer esse computador trabalhar.": "Vamos colocar esse computador em movimento.",
        "vamos fazer esse computador trabalhar.": "vamos colocar esse computador em movimento.",
    }
    for source, target in phrase_replacements.items():
        text = text.replace(source, target)

    return text


def _prepare_tts_text(text: str) -> str:
    prepared = _normalize_tts_tech_terms(text)
    prepared = _expand_negative_tts_patterns(prepared)
    prepared = _expand_currency_tts_patterns(prepared)
    prepared = _expand_percent_tts_patterns(prepared)
    prepared = _expand_general_decimal_tts_patterns(prepared)
    prepared = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", _expand_date_expression, prepared)
    prepared = _normalize_tts_punctuation(prepared)
    prepared = _expand_tts_reading_patterns(prepared)
    prepared = _restore_common_ptbr_accents(prepared)
    prepared = _massage_ptbr_pronunciation(prepared)
    prepared = _apply_abbreviation_rules(prepared)
    prepared = _apply_abbreviation_heuristics(prepared)
    prepared = _apply_pronunciation_map(prepared, _BUILTIN_TTS_PRONUNCIATIONS)
    prepared = _apply_pronunciation_map(prepared, _load_tts_pronunciations())
    prepared = re.sub(r"\bv[ęê] ésse côde\b", "vê ésse côde", prepared, flags=re.IGNORECASE)
    prepared = re.sub(r"\bvê ésse code\b", "vê ésse côde", prepared, flags=re.IGNORECASE)

    return prepared


def _wav_duration_seconds(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frame_count = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate > 0:
                return frame_count / float(frame_rate)
    except Exception:
        pass

    return 10.0


def _tts_cache_path(engine: str, text: str, settings: list[str]) -> Path:
    cache_root = Path(".tmp") / "tts_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    digest_source = "\n".join([engine, text, *settings])
    digest = hashlib.sha256(digest_source.encode("utf-8", errors="replace")).hexdigest()
    return cache_root / f"{digest}.wav"


def _load_piper_sample_rate(config_path: str) -> int:
    try:
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        audio = data.get("audio", {}) if isinstance(data, dict) else {}
        sample_rate = int(audio.get("sample_rate", 22050))
        if sample_rate > 0:
            return sample_rate
    except Exception:
        pass

    return 22050


def _piper_worker_signature(
    piper_exe: str,
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> tuple[str, ...]:
    return (
        piper_exe,
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
    )


def _stop_piper_worker_locked():
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_WARM

    process = _PIPER_WORKER_PROCESS
    _PIPER_WORKER_PROCESS = None
    _PIPER_WORKER_SIGNATURE = None
    _PIPER_WORKER_WARM = False

    if not process:
        return

    try:
        if process.stdin:
            try:
                process.stdin.close()
            except Exception:
                pass
        process.terminate()
        process.wait(timeout=1.5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _ensure_piper_worker(
    piper_exe: str,
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
):
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_SAMPLE_RATE, _PIPER_WORKER_WARM

    signature = _piper_worker_signature(
        piper_exe,
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
    )

    with _PIPER_WORKER_LOCK:
        process = _PIPER_WORKER_PROCESS
        if (
            process is not None
            and process.poll() is None
            and _PIPER_WORKER_SIGNATURE == signature
        ):
            return process

        _stop_piper_worker_locked()

        command = [
            piper_exe,
            "--model",
            model_path,
            "--output_raw",
            "--json-input",
            "--quiet",
            "--length_scale",
            length_scale,
            "--noise_scale",
            noise_scale,
            "--noise_w",
            noise_w,
        ]

        if config_path:
            command.extend(["--config", config_path])

        if speaker_id:
            command.extend(["--speaker", speaker_id])

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        _PIPER_WORKER_PROCESS = process
        _PIPER_WORKER_SIGNATURE = signature
        _PIPER_WORKER_SAMPLE_RATE = _load_piper_sample_rate(config_path)
        _PIPER_WORKER_WARM = False
        return process


def _read_piper_worker_audio(process, timeout_seconds: float, idle_seconds: float):
    global _PIPER_WORKER_WARM

    chunks = []
    started = time.monotonic()
    last_data_at = None
    effective_idle = max(idle_seconds, 0.35 if not _PIPER_WORKER_WARM else idle_seconds)

    stdout = process.stdout
    if stdout is None:
        return VoiceResult(ok=False, error="Worker Piper sem stdout."), b""

    while True:
        if speech_interrupt_pressed():
            _stop_piper_worker_locked()
            return VoiceResult(ok=False, error="Fala interrompida."), b""

        if process.poll() is not None:
            break

        now = time.monotonic()
        if now - started > timeout_seconds:
            break

        try:
            handle = msvcrt.get_osfhandle(stdout.fileno())
            total_available = ctypes.c_ulong(0)
            ok = kernel32.PeekNamedPipe(
                ctypes.c_void_p(handle),
                None,
                0,
                None,
                ctypes.byref(total_available),
                None,
            )
            available = int(total_available.value) if ok else 0
        except Exception:
            available = 0

        if available > 0:
            try:
                data = os.read(stdout.fileno(), min(available, 65536))
            except Exception:
                break
        else:
            data = b""

        if data:
            chunks.append(data)
            last_data_at = time.monotonic()
            continue

        if last_data_at is not None and (now - last_data_at) >= effective_idle:
            break

        time.sleep(0.01)

    if chunks:
        _PIPER_WORKER_WARM = True

    return None, b"".join(chunks)


def _write_raw_pcm_to_wav(output_path: str, audio_bytes: bytes, sample_rate: int):
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)


def _split_tts_text_for_piper(text: str, max_chars: int = 170) -> list[str]:
    parts = []
    raw_segments = [segment.strip() for segment in re.split(r"\n+", text) if segment.strip()]

    for segment in raw_segments:
        if len(segment) <= max_chars:
            parts.append(segment)
            continue

        comma_segments = [piece.strip() for piece in re.split(r"(?<=,)\s+", segment) if piece.strip()]
        current = ""

        for piece in comma_segments:
            candidate = piece if not current else f"{current} {piece}"
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                parts.append(current)
                current = ""

            if len(piece) <= max_chars:
                current = piece
                continue

            words = piece.split()
            buffer = ""
            for word in words:
                candidate = word if not buffer else f"{buffer} {word}"
                if len(candidate) <= max_chars:
                    buffer = candidate
                else:
                    if buffer:
                        parts.append(buffer)
                    buffer = word
            if buffer:
                current = buffer

        if current:
            parts.append(current)

    normalized_parts = [part.strip() for part in parts if part.strip()]
    merged_parts = []
    pending_prefix = ""

    for part in normalized_parts:
        compact = part.strip()
        is_tiny = len(compact) <= 6 or bool(re.fullmatch(r"\d+[.]?", compact))
        if is_tiny:
            pending_prefix = f"{pending_prefix} {compact}".strip()
            continue

        if pending_prefix:
            compact = f"{pending_prefix} {compact}".strip()
            pending_prefix = ""

        if merged_parts and re.search(r"\d+\.$", merged_parts[-1]) and re.match(r"^\d", compact):
            merged_parts[-1] = f"{merged_parts[-1][:-1]},{compact}".strip()
            continue

        merged_parts.append(compact)

    if pending_prefix:
        if merged_parts:
            merged_parts[-1] = f"{merged_parts[-1]} {pending_prefix}".strip()
        else:
            merged_parts.append(pending_prefix)

    return merged_parts


def _wait_for_wav_playback(path: str | Path) -> VoiceResult | None:
    duration_seconds = _wav_duration_seconds(path)
    started_at = time.monotonic()
    while time.monotonic() - started_at < duration_seconds + 0.15:
        if speech_interrupt_pressed():
            winsound.PlaySound(None, 0)
            return VoiceResult(ok=False, error="Fala interrompida.")
        time.sleep(0.03)

    return None


def _play_wav(path: str | Path) -> VoiceResult | None:
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    wait_for_playback = _TTS_WAIT_FOR_PLAYBACK_OVERRIDE
    if wait_for_playback is None:
        wait_for_playback = bool(VOICE_PREFERENCES.get("tts_wait_for_playback", True))
    if not wait_for_playback:
        return None

    return _wait_for_wav_playback(path)


def _play_wav_chunk(path: str | Path) -> VoiceResult | None:
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    return _wait_for_wav_playback(path)


def _voice_effect_strength() -> float:
    try:
        value = float(VOICE_PREFERENCES.get("assistant_voice_effect_strength", 0.35))
    except (TypeError, ValueError):
        return 0.35

    return max(0.0, min(1.0, value))


def _apply_jarvis_audio_effect(path: str):
    effect = str(VOICE_PREFERENCES.get("assistant_voice_effect", "")).strip().lower()
    if effect not in {"jarvis", "subtle_jarvis"}:
        return

    strength = _voice_effect_strength()
    if strength <= 0:
        return

    try:
        sample_rate, data = read_wav(path)
    except Exception:
        return

    if data.size == 0:
        return

    original_dtype = data.dtype
    audio = data.astype(np.float32)

    if np.issubdtype(original_dtype, np.integer):
        max_value = float(np.iinfo(original_dtype).max)
        audio = audio / max_value

    if audio.ndim == 1:
        audio_2d = audio[:, None]
    else:
        audio_2d = audio

    processed = audio_2d.copy()

    emphasized = processed.copy()
    emphasized[1:] = processed[1:] - (0.16 * strength * processed[:-1])
    processed = ((1.0 - (0.22 * strength)) * processed) + ((0.22 * strength) * emphasized)

    for delay_ms, gain in ((14, 0.055), (31, 0.035)):
        delay = max(1, int(sample_rate * delay_ms / 1000))
        delayed = np.zeros_like(processed)
        delayed[delay:] = processed[:-delay]
        processed += delayed * gain * strength

    drive = 1.0 + (1.2 * strength)
    processed = np.tanh(processed * drive) / np.tanh(drive)

    peak = float(np.max(np.abs(processed))) if processed.size else 0.0
    if peak > 0:
        processed = processed * min(0.92 / peak, 1.0)

    if audio.ndim == 1:
        processed = processed[:, 0]

    output = np.clip(processed, -1.0, 1.0)
    output = (output * 32767.0).astype(np.int16)

    try:
        write_wav(path, sample_rate, output)
    except Exception:
        pass


def _piper_cache_settings(
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> list[str]:
    effect = str(VOICE_PREFERENCES.get("assistant_voice_effect", "")).strip().lower()
    effect_strength = str(VOICE_PREFERENCES.get("assistant_voice_effect_strength", 0.0))
    return [
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
        effect,
        effect_strength,
    ]


def _run_piper_synthesis(
    text_for_tts: str,
    output_path: str,
    piper_exe: str,
    model: Path,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> VoiceResult | None:
    worker_enabled = bool(VOICE_PREFERENCES.get("piper_persistent_worker_enabled", True))
    worker_fallback = bool(VOICE_PREFERENCES.get("piper_worker_fallback_to_cli", True))
    worker_timeout = _float_pref("piper_worker_timeout_seconds", 20.0, 3.0, 60.0)
    worker_idle = _float_pref("piper_worker_idle_seconds", 0.12, 0.03, 1.0)

    if worker_enabled:
        try:
            process = _ensure_piper_worker(
                piper_exe,
                str(model),
                config_path,
                speaker_id,
                length_scale,
                noise_scale,
                noise_w,
            )

            payload = json.dumps({"text": text_for_tts}, ensure_ascii=False).encode("utf-8") + b"\n"

            with _PIPER_WORKER_LOCK:
                if process.poll() is not None:
                    raise RuntimeError("Worker Piper morreu antes da escrita.")
                if process.stdin is None:
                    raise RuntimeError("Worker Piper sem stdin.")
                process.stdin.write(payload)
                process.stdin.flush()

            interrupt_result, audio_bytes = _read_piper_worker_audio(
                process,
                timeout_seconds=worker_timeout,
                idle_seconds=worker_idle,
            )

            if interrupt_result:
                return interrupt_result

            if audio_bytes:
                _write_raw_pcm_to_wav(output_path, audio_bytes, _PIPER_WORKER_SAMPLE_RATE)
                _apply_jarvis_audio_effect(output_path)
                return None

            with _PIPER_WORKER_LOCK:
                _stop_piper_worker_locked()

        except Exception as exc:
            with _PIPER_WORKER_LOCK:
                _stop_piper_worker_locked()

            if not worker_fallback:
                return VoiceResult(ok=False, error=f"Worker persistente do Piper falhou: {exc}")

        if not worker_fallback:
            return VoiceResult(ok=False, error="Worker persistente do Piper falhou.")

    command = [
        piper_exe,
        "--model",
        str(model),
        "--output_file",
        output_path,
        "--length_scale",
        length_scale,
        "--noise_scale",
        noise_scale,
        "--noise_w",
        noise_w,
    ]

    if config_path:
        command.extend(["--config", config_path])

    if speaker_id:
        command.extend(["--speaker", speaker_id])

    try:
        completed = subprocess.run(
            command,
            input=text_for_tts,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return VoiceResult(ok=False, error=f"Piper nao encontrado: {piper_exe}")
    except subprocess.TimeoutExpired:
        return VoiceResult(ok=False, error="Tempo limite atingido ao falar com Piper.")
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao usar Piper: {exc}")

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        return VoiceResult(ok=False, error=error or "Piper nao conseguiu gerar audio.")

    _apply_jarvis_audio_effect(output_path)
    return None


def prime_piper_cache(phrases: list[str]) -> VoiceResult:
    piper_exe = str(VOICE_PREFERENCES.get("piper_exe_path", "piper")).strip() or "piper"
    model_path = str(VOICE_PREFERENCES.get("piper_model_path", "")).strip()
    config_path = str(VOICE_PREFERENCES.get("piper_config_path", "")).strip()
    speaker_id = str(VOICE_PREFERENCES.get("piper_speaker_id", "")).strip()
    length_scale = _float_setting("piper_length_scale", 1.0)
    noise_scale = _float_setting("piper_noise_scale", 0.667)
    noise_w = _float_setting("piper_noise_w", 0.8)

    if not model_path:
        return VoiceResult(ok=False, error="Modelo do Piper nao configurado.")

    model = Path(model_path)
    if not model.exists():
        return VoiceResult(ok=False, error=f"Modelo do Piper nao encontrado: {model_path}")

    if config_path and not Path(config_path).exists():
        return VoiceResult(ok=False, error=f"Config do Piper nao encontrado: {config_path}")

    warmed = 0
    skipped = 0
    errors = []

    for phrase in phrases:
        phrase = str(phrase).strip()
        if not phrase:
            continue

        text_for_tts = _prepare_tts_text(phrase)
        cache_path = _tts_cache_path(
            "piper",
            text_for_tts,
            _piper_cache_settings(
                str(model),
                config_path,
                speaker_id,
                length_scale,
                noise_scale,
                noise_w,
            ),
        )
        if cache_path.exists():
            skipped += 1
            continue

        command = [
            piper_exe,
            "--model",
            str(model),
            "--output_file",
            str(cache_path),
            "--length_scale",
            length_scale,
            "--noise_scale",
            noise_scale,
            "--noise_w",
            noise_w,
        ]

        if config_path:
            command.extend(["--config", config_path])

        if speaker_id:
            command.extend(["--speaker", speaker_id])

        try:
            completed = subprocess.run(
                command,
                input=text_for_tts,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except Exception as exc:
            errors.append(str(exc))
            continue

        if completed.returncode != 0:
            errors.append((completed.stderr or completed.stdout or "Piper falhou.").strip())
            try:
                cache_path.unlink(missing_ok=True)
            except Exception:
                pass
            continue

        _apply_jarvis_audio_effect(str(cache_path))
        warmed += 1

    if errors:
        return VoiceResult(
            ok=False,
            text=f"Cache TTS: {warmed} criado(s), {skipped} ja existia(m).",
            error=errors[0],
        )

    return VoiceResult(ok=True, text=f"Cache TTS: {warmed} criado(s), {skipped} ja existia(m).")


def _speak_with_piper(text: str) -> VoiceResult:
    text_for_tts = _prepare_tts_text(text)
    piper_exe = str(VOICE_PREFERENCES.get("piper_exe_path", "piper")).strip() or "piper"
    model_path = str(VOICE_PREFERENCES.get("piper_model_path", "")).strip()
    config_path = str(VOICE_PREFERENCES.get("piper_config_path", "")).strip()
    speaker_id = str(VOICE_PREFERENCES.get("piper_speaker_id", "")).strip()
    length_scale = _float_setting("piper_length_scale", 1.0)
    noise_scale = _float_setting("piper_noise_scale", 0.667)
    noise_w = _float_setting("piper_noise_w", 0.8)

    if not model_path:
        return VoiceResult(ok=False, error="Modelo do Piper nao configurado.")

    model = Path(model_path)
    if not model.exists():
        return VoiceResult(ok=False, error=f"Modelo do Piper nao encontrado: {model_path}")

    if config_path and not Path(config_path).exists():
        return VoiceResult(ok=False, error=f"Config do Piper nao encontrado: {config_path}")

    cache_settings = _piper_cache_settings(
        str(model),
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
    )

    cache_path = None
    if bool(VOICE_PREFERENCES.get("tts_cache_enabled", True)):
        cache_path = _tts_cache_path(
            "piper",
            text_for_tts,
            cache_settings,
        )
        if cache_path.exists():
            interrupted = _play_wav(cache_path)
            if interrupted:
                return interrupted
            return VoiceResult(ok=True, text=text)

    chunk_threshold = 140
    chunked_parts = _split_tts_text_for_piper(text_for_tts)
    should_chunk = len(chunked_parts) > 1 and len(text_for_tts) >= chunk_threshold

    if should_chunk:
        for chunk_text in chunked_parts:
            chunk_cache_path = None
            if bool(VOICE_PREFERENCES.get("tts_cache_enabled", True)):
                chunk_cache_path = _tts_cache_path("piper", chunk_text, cache_settings)
                if chunk_cache_path.exists():
                    interrupted = _play_wav_chunk(chunk_cache_path)
                    if interrupted:
                        return interrupted
                    continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                chunk_output_path = temp_file.name

            try:
                error_result = _run_piper_synthesis(
                    chunk_text,
                    chunk_output_path,
                    piper_exe,
                    model,
                    config_path,
                    speaker_id,
                    length_scale,
                    noise_scale,
                    noise_w,
                )
                if error_result:
                    return error_result

                play_path = chunk_output_path
                if chunk_cache_path:
                    shutil.copy2(chunk_output_path, chunk_cache_path)
                    play_path = str(chunk_cache_path)

                interrupted = _play_wav_chunk(play_path)
                if interrupted:
                    return interrupted
            finally:
                try:
                    Path(chunk_output_path).unlink(missing_ok=True)
                except Exception:
                    pass

        return VoiceResult(ok=True, text=text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    try:
        error_result = _run_piper_synthesis(
            text_for_tts,
            output_path,
            piper_exe,
            model,
            config_path,
            speaker_id,
            length_scale,
            noise_scale,
            noise_w,
        )
        if error_result:
            return error_result
        play_path = output_path
        if cache_path:
            shutil.copy2(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = _play_wav(play_path)
        if interrupted:
            return interrupted

        return VoiceResult(ok=True, text=text)
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _gemini_cache_settings(voice_name: str, language_code: str, timeout_seconds: str) -> list[str]:
    effect = str(VOICE_PREFERENCES.get("assistant_voice_effect", "")).strip().lower()
    effect_strength = str(VOICE_PREFERENCES.get("assistant_voice_effect_strength", 0.0))
    return [voice_name, language_code, timeout_seconds, effect, effect_strength]


def _speak_with_gemini(text: str) -> VoiceResult:
    text_for_tts = _prepare_tts_text(text)
    voice_name = str(VOICE_PREFERENCES.get("gemini_tts_voice_name", "Kore")).strip() or "Kore"
    language_code = str(VOICE_PREFERENCES.get("gemini_tts_language_code", "pt-BR")).strip() or "pt-BR"
    timeout_seconds = _int_pref("gemini_tts_timeout_seconds", 60, 10, 180)

    cache_path = None
    cache_enabled = bool(VOICE_PREFERENCES.get("tts_cache_enabled", True))
    if cache_enabled:
        cache_path = _tts_cache_path(
            "gemini",
            text_for_tts,
            _gemini_cache_settings(voice_name, language_code, str(timeout_seconds)),
        )
        if cache_path.exists():
            interrupted = _play_wav(cache_path)
            if interrupted:
                return interrupted
            return VoiceResult(ok=True, text=text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    try:
        synthesize_gemini_tts_to_wav(
            text_for_tts,
            output_path,
            voice_name=voice_name,
            language_code=language_code,
            timeout_seconds=timeout_seconds,
        )
        _apply_jarvis_audio_effect(output_path)

        play_path = output_path
        if cache_path:
            shutil.copy2(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = _play_wav(play_path)
        if interrupted:
            return interrupted

        return VoiceResult(ok=True, text=text)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Gemini TTS falhou: {exc}")
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _speak_with_windows(text: str, culture: str | None = None) -> VoiceResult:
    selected_culture = culture or str(VOICE_PREFERENCES.get("tts_voice_culture", "pt-BR"))
    preferred_voice_name = str(VOICE_PREFERENCES.get("tts_voice_name", "")).strip()
    tts_rate = _clamp_int(VOICE_PREFERENCES.get("tts_rate", 0), -10, 10, 0)
    tts_volume = _clamp_int(VOICE_PREFERENCES.get("tts_volume", 100), 0, 100, 100)
    safe_text = text.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Speech
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$preferredVoiceName = "{preferred_voice_name.replace('"', '`"')}"

try {{
    $voice.Rate = {tts_rate}
    $voice.Volume = {tts_volume}
    $selected = $null

    if ($preferredVoiceName) {{
        $selected = $voice.GetInstalledVoices() |
            Where-Object {{ $_.VoiceInfo.Name -eq $preferredVoiceName }} |
            Select-Object -First 1
    }}

    if (-not $selected) {{
        $selected = $voice.GetInstalledVoices() |
            Where-Object {{ $_.VoiceInfo.Culture.Name -eq "{selected_culture}" }} |
            Select-Object -First 1
    }}

    if ($selected) {{
        $voice.SelectVoice($selected.VoiceInfo.Name)
    }}

    $voice.Speak('{safe_text}')
    Write-Output "__OK__"
}} catch {{
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}} finally {{
    $voice.Dispose()
}}
"""

    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")

    try:
        process = subprocess.Popen(
            [
                POWERSHELL_EXE,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        started_at = time.monotonic()
        while process.poll() is None:
            if speech_interrupt_pressed():
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                return VoiceResult(ok=False, error="Fala interrompida.")

            if time.monotonic() - started_at > 20:
                process.kill()
                return VoiceResult(ok=False, error="Tempo limite atingido ao falar a resposta.")

            time.sleep(0.03)

        stdout, stderr = process.communicate()
        completed = subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao iniciar voz sintetizada: {exc}")

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        return VoiceResult(ok=False, error=stderr or "Sintese de voz indisponivel.")

    stdout = (completed.stdout or "").strip()
    if stdout.startswith("__ERROR__:"):
        message = stdout.split("__ERROR__:", 1)[1].strip()
        return VoiceResult(ok=False, error=message or "Sintese de voz indisponivel.")

    return VoiceResult(ok=True, text=text)


def listen_for_hotword(hotword: str = HOTWORD) -> VoiceResult:
    try:
        audio = _record_audio(
            HOTWORD_TIMEOUT_SECONDS,
            min_speech_seconds=HOTWORD_MIN_SPEECH_SECONDS,
            max_silence_seconds=HOTWORD_MAX_SILENCE_SECONDS,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    result = _transcribe_audio(
        audio=audio,
        model_size=HOTWORD_MODEL_SIZE,
        prompt=HOTWORD_PROMPT,
        beam_size=WHISPER_HOTWORD_BEAM_SIZE,
        best_of=WHISPER_HOTWORD_BEST_OF,
        vad_filter=WHISPER_HOTWORD_VAD_FILTER,
    )

    if not result.ok:
        return result

    if _contains_hotword(result.text, hotword):
        command_result = _transcribe_audio(
            audio=audio,
            model_size=COMMAND_MODEL_SIZE,
            prompt=COMMAND_PROMPT,
            beam_size=WHISPER_COMMAND_BEAM_SIZE,
            best_of=WHISPER_COMMAND_BEST_OF,
            vad_filter=WHISPER_COMMAND_VAD_FILTER,
        )
        if command_result.ok:
            inline_command = _extract_inline_command(command_result.text, hotword)
            return VoiceResult(
                ok=True,
                text=result.text,
                command_text=inline_command,
            )

        return VoiceResult(ok=True, text=result.text)

    return VoiceResult(ok=False, error="Hotword nao detectada.")


def listen_once(timeout_seconds: int = 6, culture: str = "pt") -> VoiceResult:
    del culture

    try:
        audio = _record_audio(timeout_seconds)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    return _transcribe_audio(
        audio=audio,
        model_size=COMMAND_MODEL_SIZE,
        prompt=COMMAND_PROMPT,
        beam_size=WHISPER_COMMAND_BEAM_SIZE,
        best_of=WHISPER_COMMAND_BEST_OF,
        vad_filter=WHISPER_COMMAND_VAD_FILTER,
    )


def listen_conversation_once(timeout_seconds: float | None = None, culture: str = "pt") -> VoiceResult:
    del culture

    try:
        audio = _record_audio(
            timeout_seconds or CONVERSATION_TIMEOUT_SECONDS,
            min_speech_seconds=CONVERSATION_MIN_SPEECH_SECONDS,
            max_silence_seconds=CONVERSATION_MAX_SILENCE_SECONDS,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    return _transcribe_audio(
        audio=audio,
        model_size=CONVERSATION_MODEL_SIZE,
        prompt=CONVERSATION_PROMPT,
        beam_size=WHISPER_CONVERSATION_BEAM_SIZE,
        best_of=WHISPER_CONVERSATION_BEST_OF,
        vad_filter=WHISPER_CONVERSATION_VAD_FILTER,
    )


def speak(
    text: str,
    culture: str | None = None,
    *,
    interrupt_current: bool = False,
    wait_for_playback: bool | None = None,
) -> VoiceResult:
    global _TTS_WAIT_FOR_PLAYBACK_OVERRIDE

    if not text:
        return VoiceResult(ok=False, error="Nada para falar.")

    if not bool(VOICE_PREFERENCES.get("tts_enabled", True)):
        return VoiceResult(ok=True, text=text)

    previous_wait_override = _TTS_WAIT_FOR_PLAYBACK_OVERRIDE
    _TTS_WAIT_FOR_PLAYBACK_OVERRIDE = wait_for_playback

    if interrupt_current:
        try:
            winsound.PlaySound(None, 0)
        except Exception:
            pass

    try:
        engine = str(VOICE_PREFERENCES.get("tts_engine", "windows")).strip().lower()

        if engine == "gemini":
            result = _speak_with_gemini(text)
            if (
                result.ok
                or result.error == "Fala interrompida."
                or not bool(VOICE_PREFERENCES.get("gemini_tts_fallback_to_piper", True))
            ):
                return result

            if str(VOICE_PREFERENCES.get("piper_model_path", "")).strip():
                piper_result = _speak_with_piper(text)
                if piper_result.ok or piper_result.error == "Fala interrompida.":
                    return piper_result

            return _speak_with_windows(text, culture=culture)

        if engine == "piper":
            result = _speak_with_piper(text)
            if (
                result.ok
                or result.error == "Fala interrompida."
                or not bool(VOICE_PREFERENCES.get("piper_fallback_to_windows", True))
            ):
                return result

        return _speak_with_windows(text, culture=culture)
    finally:
        _TTS_WAIT_FOR_PLAYBACK_OVERRIDE = previous_wait_override

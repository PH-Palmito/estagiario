import base64
import ctypes
import os
import re
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

import difflib
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError
from memory.voice_preferences import load_voice_preferences
from scipy.io.wavfile import write as write_wav


POWERSHELL_EXE = "powershell"
user32 = ctypes.windll.user32
SAMPLE_RATE = 16000
COMMAND_MODEL_SIZE = "small"
HOTWORD_MODEL_SIZE = "tiny"
FRAME_SIZE = 1024
DEFAULT_MAX_RECORD_SECONDS = 6.0
VOICE_PREFERENCES = load_voice_preferences()
CONVERSATION_MODEL_SIZE = str(VOICE_PREFERENCES.get("conversation_model_size", COMMAND_MODEL_SIZE))


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
    "Assistente local chamado estagiario. Transcreva comandos curtos em portugues do Brasil. "
    "Vocabulário esperado: estagiario, abre, abrir, fecha, fechar, foca, focar, troca, "
    "minimiza, minimizar, maximiza, maximizar, restaura, restaurar, nova aba, fechar aba, "
    "proxima aba, aba anterior, de novo, pesquisar. "
    "Aplicativos e sites esperados: chrome, google chrome, youtube, google, vscode, vs code, "
    "code, spotify, whatsapp, zap, bloco de notas, notas, powershell, edge, explorador de arquivos, "
    "github, git hub, android studio, epic games, steam. "
    "Exemplos: estagiario abre o chrome; abre o vscode; minimiza o chrome; maximiza code; "
    "fecha o spotify; abre nova aba; fechar aba; estagiario abre spotify."
)
COMMAND_PROMPT = (
    "Comandos curtos em portugues do Brasil para controlar o computador. "
    "Verbos comuns: abrir, fechar, focar, trocar, minimizar, maximizar, restaurar, pesquisar, ler, selecionar. "
    "Alvos comuns: chrome, youtube, google, vscode, code, spotify, whatsapp, zap, bloco de notas, "
    "powershell, edge, github, android studio, steam, mercado livre, magalu."
)
CONVERSATION_PROMPT = str(
    VOICE_PREFERENCES.get(
        "conversation_transcription_prompt",
        "Conversa casual em portugues do Brasil.",
    )
).strip()
HOTWORD_PROMPT = f"Palavra de ativacao: {HOTWORD}."

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
    input_device = sd.default.device[0]
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
    input_device = sd.default.device[0]
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

    temp_path = None
    try:
        processed_audio = _preprocess_audio(audio) if preprocess else audio
        temp_path = _save_temp_wav(processed_audio)
        model = _get_model(model_size)
        segments, info = model.transcribe(
            temp_path,
            language="pt",
            task="transcribe",
            vad_filter=vad_filter,
            beam_size=beam_size,
            best_of=best_of,
            temperature=0.0,
            initial_prompt=prompt or None,
            condition_on_previous_text=False,
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()

        if not text:
            return VoiceResult(ok=False, error="Nenhuma fala reconhecida.")

        if info.language_probability is not None and info.language_probability < 0.25:
            return VoiceResult(ok=True, text=text)

        return VoiceResult(ok=True, text=text)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao transcrever audio: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


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
    except RuntimeError:
        winsound.MessageBeep()


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


def _prepare_tts_text(text: str) -> str:
    replacements = {
        "spotify": "ispótifai",
        "Spotify": "Ispótifai",
        "github": "guít rãb",
        "GitHub": "Guít rãb",
        "youtube": "iutúbi",
        "YouTube": "Iutúbi",
        "chatgpt": "chát g p t",
        "ChatGPT": "Chát g p t",
        "vscode": "v s côd",
        "VSCode": "v s côd",
        "code": "côd",
        "Chrome": "Crôme",
        "chrome": "crôme",
    }

    prepared = text
    for source, target in replacements.items():
        prepared = re.sub(rf"\b{re.escape(source)}\b", target, prepared)

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


def _speak_with_piper(text: str) -> VoiceResult:
    text_for_tts = _prepare_tts_text(text)
    piper_exe = str(VOICE_PREFERENCES.get("piper_exe_path", "piper")).strip() or "piper"
    model_path = str(VOICE_PREFERENCES.get("piper_model_path", "")).strip()
    config_path = str(VOICE_PREFERENCES.get("piper_config_path", "")).strip()
    speaker_id = str(VOICE_PREFERENCES.get("piper_speaker_id", "")).strip()

    if not model_path:
        return VoiceResult(ok=False, error="Modelo do Piper nao configurado.")

    model = Path(model_path)
    if not model.exists():
        return VoiceResult(ok=False, error=f"Modelo do Piper nao encontrado: {model_path}")

    if config_path and not Path(config_path).exists():
        return VoiceResult(ok=False, error=f"Config do Piper nao encontrado: {config_path}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    command = [
        piper_exe,
        "--model",
        str(model),
        "--output_file",
        output_path,
        "--length_scale",
        _float_setting("piper_length_scale", 1.0),
        "--noise_scale",
        _float_setting("piper_noise_scale", 0.667),
        "--noise_w",
        _float_setting("piper_noise_w", 0.8),
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

        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "").strip()
            return VoiceResult(ok=False, error=error or "Piper nao conseguiu gerar audio.")

        duration_seconds = _wav_duration_seconds(output_path)
        winsound.PlaySound(output_path, winsound.SND_FILENAME | winsound.SND_ASYNC)

        started_at = time.monotonic()
        while time.monotonic() - started_at < duration_seconds + 0.15:
            if speech_interrupt_pressed():
                winsound.PlaySound(None, 0)
                return VoiceResult(ok=False, error="Fala interrompida.")
            time.sleep(0.03)

        return VoiceResult(ok=True, text=text)
    except FileNotFoundError:
        return VoiceResult(ok=False, error=f"Piper nao encontrado: {piper_exe}")
    except subprocess.TimeoutExpired:
        return VoiceResult(ok=False, error="Tempo limite atingido ao falar com Piper.")
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao usar Piper: {exc}")
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


def speak(text: str, culture: str | None = None) -> VoiceResult:
    if not text:
        return VoiceResult(ok=False, error="Nada para falar.")

    if not bool(VOICE_PREFERENCES.get("tts_enabled", True)):
        return VoiceResult(ok=True, text=text)

    engine = str(VOICE_PREFERENCES.get("tts_engine", "windows")).strip().lower()

    if engine == "piper":
        result = _speak_with_piper(text)
        if (
            result.ok
            or result.error == "Fala interrompida."
            or not bool(VOICE_PREFERENCES.get("piper_fallback_to_windows", True))
        ):
            return result

    return _speak_with_windows(text, culture=culture)

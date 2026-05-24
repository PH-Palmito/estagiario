from __future__ import annotations

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError

_models = {}


def model_repo(model_size: str) -> str:
    return f"Systran/faster-whisper-{model_size}"


def get_model(model_size: str) -> WhisperModel:
    model = _models.get(model_size)
    if model is not None:
        return model

    repo = model_repo(model_size)
    try:
        model_path = snapshot_download(repo, local_files_only=True)
    except LocalEntryNotFoundError:
        model_path = snapshot_download(repo, local_files_only=False)

    model = WhisperModel(model_path, device="cpu", compute_type="int8")
    _models[model_size] = model
    return model


def clear_model_cache():
    _models.clear()

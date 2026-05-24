from core.router_apps import APP_DETECTORS
from core.router_basic import BASIC_EARLY_DETECTORS, BASIC_LATE_DETECTORS
from core.router_browser import BROWSER_DETECTORS
from core.router_browser_controls import BROWSER_CONTROL_DETECTORS
from core.router_code import CODE_DETECTORS
from core.router_conversation import CONVERSATION_DETECTORS
from core.router_daily import DAILY_DETECTORS
from core.router_fast_path import FAST_PATH_DETECTORS
from core.router_files import FILE_DETECTORS
from core.router_image import IMAGE_DETECTORS
from core.router_investments import (
    INVESTMENT_BROWSER_DETECTORS,
    INVESTMENT_QUESTION_DETECTORS,
    INVESTMENT_STRATEGY_DETECTORS,
)
from core.router_macros import MACRO_DETECTORS
from core.router_media import MEDIA_DETECTORS
from core.router_memory import MEMORY_DETECTORS
from core.router_music import MUSIC_DETECTORS
from core.router_screen import SCREEN_DETECTORS
from core.router_site_search import SITE_SEARCH_DETECTORS
from core.router_system import SYSTEM_DETECTORS, SYSTEM_INPUT_DETECTORS
from core.router_vision import VISION_DETECTORS
from core.router_voice import VOICE_DETECTORS

DETECTOR_GROUPS = [
    ("fast_path", FAST_PATH_DETECTORS),
    ("macros", MACRO_DETECTORS),
    ("files", FILE_DETECTORS),
    ("investment_strategy", INVESTMENT_STRATEGY_DETECTORS),
    ("system_input", SYSTEM_INPUT_DETECTORS),
    ("basic_early", BASIC_EARLY_DETECTORS),
    ("memory", MEMORY_DETECTORS),
    ("voice", VOICE_DETECTORS),
    ("code", CODE_DETECTORS),
    ("screen", SCREEN_DETECTORS),
    ("browser_controls", BROWSER_CONTROL_DETECTORS),
    ("music", MUSIC_DETECTORS),
    ("investment_browser", INVESTMENT_BROWSER_DETECTORS),
    ("site_search", SITE_SEARCH_DETECTORS),
    ("media", MEDIA_DETECTORS),
    ("system", SYSTEM_DETECTORS),
    ("daily", DAILY_DETECTORS),
    ("investment_questions", INVESTMENT_QUESTION_DETECTORS),
    ("browser", BROWSER_DETECTORS),
    ("image", IMAGE_DETECTORS),
    ("vision", VISION_DETECTORS),
    ("apps", APP_DETECTORS),
    ("basic_late", BASIC_LATE_DETECTORS),
    ("conversation", CONVERSATION_DETECTORS),
]


def iter_detectors():
    for group_name, detectors in DETECTOR_GROUPS:
        for detector in detectors:
            yield group_name, detector


def route(user_input: str):
    for _group_name, detector in iter_detectors():
        result = detector(user_input)
        if result:
            return result

    return {"intent": "respond", "target": None, "response": "Nao entendi."}

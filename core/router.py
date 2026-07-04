from core.router_apps import APP_DETECTORS
from core.router_basic import BASIC_EARLY_DETECTORS, BASIC_LATE_DETECTORS
from core.router_browser import BROWSER_DETECTORS
from core.router_browser_controls import BROWSER_CONTROL_DETECTORS
from core.router_code import CODE_DETECTORS
from core.router_conversation import CONVERSATION_DETECTORS, GENERAL_QUESTION_DETECTORS
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
from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
    build_detector_groups,
    detector_group_tuples,
    find_detector_match,
    iter_group_detectors,
    trace_route,
)

ROUTER_GROUP_DEFINITIONS = [
    ("fast_path", FAST_PATH_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("macros", MACRO_DETECTORS, INTENT_LEVEL_COMPOSITE_TASK),
    ("files", FILE_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("investment_strategy", INVESTMENT_STRATEGY_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("system_input", SYSTEM_INPUT_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("basic_early", BASIC_EARLY_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("general_questions", GENERAL_QUESTION_DETECTORS, INTENT_LEVEL_CONVERSATION),
    ("memory", MEMORY_DETECTORS, INTENT_LEVEL_QUESTION),
    ("voice", VOICE_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("code", CODE_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("screen", SCREEN_DETECTORS, INTENT_LEVEL_QUESTION),
    ("browser_controls", BROWSER_CONTROL_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("music", MUSIC_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("investment_browser", INVESTMENT_BROWSER_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("site_search", SITE_SEARCH_DETECTORS, INTENT_LEVEL_QUESTION),
    ("media", MEDIA_DETECTORS, INTENT_LEVEL_COMPOSITE_TASK),
    ("system", SYSTEM_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("daily", DAILY_DETECTORS, INTENT_LEVEL_QUESTION),
    ("investment_questions", INVESTMENT_QUESTION_DETECTORS, INTENT_LEVEL_QUESTION),
    ("browser", BROWSER_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("image", IMAGE_DETECTORS, INTENT_LEVEL_QUESTION),
    ("vision", VISION_DETECTORS, INTENT_LEVEL_QUESTION),
    ("apps", APP_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("basic_late", BASIC_LATE_DETECTORS, INTENT_LEVEL_DIRECT_COMMAND),
    ("conversation", CONVERSATION_DETECTORS, INTENT_LEVEL_CONVERSATION),
]

ROUTER_GROUPS = build_detector_groups(ROUTER_GROUP_DEFINITIONS)
DETECTOR_GROUPS = detector_group_tuples(ROUTER_GROUPS)


def iter_detectors():
    yield from iter_group_detectors(ROUTER_GROUPS)


def route_match(user_input: str):
    return find_detector_match(user_input, ROUTER_GROUPS)


def route_trace(user_input: str):
    return trace_route(user_input, ROUTER_GROUPS)


def route(user_input: str):
    match = route_match(user_input)
    if match:
        return match.result

    return {"intent": "respond", "target": None, "response": "Nao entendi."}

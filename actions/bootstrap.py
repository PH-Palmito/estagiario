from __future__ import annotations

from actions.background_actions import register_background_actions
from actions.file_actions import register_file_actions
from actions.investment_actions import register_investment_actions
from actions.legacy_browser_actions import register_legacy_browser_actions
from actions.legacy_control_actions import register_legacy_control_actions
from actions.legacy_misc_actions import register_legacy_misc_actions
from actions.legacy_read_actions import register_legacy_read_actions
from actions.legacy_sensitive_actions import register_legacy_sensitive_actions
from actions.legacy_vision_actions import register_legacy_vision_actions
from actions.legacy_write_actions import register_legacy_write_actions
from actions.memory_actions import register_memory_actions
from actions.memory_backup_actions import register_memory_backup_actions
from actions.study_actions import register_study_actions
from actions.training_actions import register_training_actions
from actions.whatsapp_actions import register_whatsapp_actions

_BOOTSTRAPPED = False


def ensure_default_actions() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    register_background_actions()
    register_file_actions()
    register_memory_actions()
    register_memory_backup_actions()
    register_study_actions()
    register_training_actions()
    register_whatsapp_actions()
    register_investment_actions()
    register_legacy_read_actions()
    register_legacy_write_actions()
    register_legacy_sensitive_actions()
    register_legacy_control_actions()
    register_legacy_browser_actions()
    register_legacy_misc_actions()
    register_legacy_vision_actions()
    _BOOTSTRAPPED = True

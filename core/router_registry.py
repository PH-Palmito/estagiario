from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

RawAction = dict
Detector = Callable[[str], RawAction | None]

INTENT_LEVEL_DIRECT_COMMAND = "comando_direto"
INTENT_LEVEL_QUESTION = "pergunta"
INTENT_LEVEL_COMPOSITE_TASK = "tarefa_composta"
INTENT_LEVEL_CONVERSATION = "conversa"
VALID_INTENT_LEVELS = {
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
}


@dataclass(frozen=True)
class DetectorGroup:
    name: str
    detectors: tuple[Detector, ...]
    priority: int
    description: str = ""
    intent_level: str = INTENT_LEVEL_DIRECT_COMMAND


@dataclass(frozen=True)
class DetectorMatch:
    group_name: str
    detector_name: str
    result: RawAction
    intent_level: str = INTENT_LEVEL_DIRECT_COMMAND


@dataclass(frozen=True)
class RouteTrace:
    match: DetectorMatch | None
    checked_detectors: int
    checked_groups: tuple[str, ...]


def build_detector_groups(groups: Iterable[tuple[str, Iterable[Detector]]]) -> tuple[DetectorGroup, ...]:
    detector_groups: list[DetectorGroup] = []
    for index, definition in enumerate(groups):
        name, detectors, *extras = definition
        intent_level = str(extras[0] if extras else INTENT_LEVEL_DIRECT_COMMAND)
        if intent_level not in VALID_INTENT_LEVELS:
            intent_level = INTENT_LEVEL_DIRECT_COMMAND
        detector_groups.append(
            DetectorGroup(
                name=name,
                detectors=tuple(detectors),
                priority=index,
                intent_level=intent_level,
            )
        )
    return tuple(detector_groups)


def detector_group_tuples(groups: Iterable[DetectorGroup]) -> list[tuple[str, tuple[Detector, ...]]]:
    return [(group.name, group.detectors) for group in groups]


def iter_group_detectors(groups: Iterable[DetectorGroup]):
    for group in groups:
        for detector in group.detectors:
            yield group.name, detector


def find_detector_match(user_input: str, groups: Iterable[DetectorGroup]) -> DetectorMatch | None:
    for group in groups:
        for detector in group.detectors:
            result = detector(user_input)
            if result:
                return DetectorMatch(
                    group_name=group.name,
                    detector_name=getattr(detector, "__name__", detector.__class__.__name__),
                    result=result,
                    intent_level=group.intent_level,
                )
    return None


def trace_route(user_input: str, groups: Iterable[DetectorGroup]) -> RouteTrace:
    checked = 0
    checked_groups: list[str] = []
    for group in groups:
        checked_groups.append(group.name)
        for detector in group.detectors:
            checked += 1
            result = detector(user_input)
            if result:
                return RouteTrace(
                    match=DetectorMatch(
                        group_name=group.name,
                        detector_name=getattr(detector, "__name__", detector.__class__.__name__),
                        result=result,
                        intent_level=group.intent_level,
                    ),
                    checked_detectors=checked,
                    checked_groups=tuple(checked_groups),
                )
    return RouteTrace(
        match=None,
        checked_detectors=checked,
        checked_groups=tuple(checked_groups),
    )

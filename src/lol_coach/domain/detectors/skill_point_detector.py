"""Detecta pontos de skill disponíveis após level up."""
from __future__ import annotations

from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.state_diff import StateDiff
from lol_coach.settings.constants import EventPriority, EventTags, GameRules, Timing
from lol_coach.settings.messages import TTSMessages

_SKILL_BY_CODE: dict[int, str] = {1: "Q", 2: "W", 3: "E", 4: "R"}


class SkillPointDetector:
    """Avisa quando o jogador tem pontos de skill para gastar.

    Emite o aviso imediatamente quando o jogador sobe de nível e repete em
    intervalos regulares enquanto houver pontos parados. A recomendação de
    qual skill upar vem da `skill_sequence` por nível (preferida) ou da
    `skill_priority` Q/W/E como fallback.
    """

    def __init__(
        self,
        skill_priority: list[str] | None = None,
        skill_sequence: list[int] | None = None,
    ) -> None:
        self._last_reminder_at_seconds: float = 0.0
        self._skill_priority = list(skill_priority) if skill_priority else []
        self._skill_sequence = list(skill_sequence) if skill_sequence else []

    def update_recommendations(
        self,
        skill_priority: list[str] | None = None,
        skill_sequence: list[int] | None = None,
    ) -> None:
        """Permite injetar a build depois que o detector já está rodando."""
        if skill_sequence:
            self._skill_sequence = list(skill_sequence)
        elif skill_priority:
            self._skill_priority = list(skill_priority)

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        available = diff.available_skill_points
        if available == 0:
            return []

        now = diff.current.game_time_seconds
        just_gained = available > diff.previous_available_skill_points
        due_reminder = (
            now - self._last_reminder_at_seconds
            >= Timing.SKILL_REMINDER_INTERVAL_SECONDS
        )

        if not just_gained and not due_reminder:
            return []

        self._last_reminder_at_seconds = now

        recommended = self._pick_skill_to_level(diff)
        if recommended:
            message = TTSMessages.skill_point_with_recommendation(recommended)
        elif available == 1:
            message = TTSMessages.skill_point_generic()
        else:
            message = TTSMessages.skill_points_accumulated(available)

        priority = (
            EventPriority.SKILL_GAINED if just_gained else EventPriority.SKILL_REMINDER
        )
        return [CoachEvent(message=message, priority=priority, tag=EventTags.SKILL)]

    def _pick_skill_to_level(self, diff: StateDiff) -> str | None:
        """Decide qual skill upar com base na build carregada."""
        abilities = diff.current.abilities

        if self._skill_sequence:
            total_spent = abilities.total_points_spent
            if total_spent < len(self._skill_sequence):
                return _SKILL_BY_CODE.get(self._skill_sequence[total_spent])
            return None

        if not self._skill_priority:
            return None

        unlocked_ult_ranks = sum(
            1
            for unlock_level in GameRules.ULTIMATE_UNLOCK_LEVELS
            if diff.current.player_level >= unlock_level
        )
        if abilities.r < min(GameRules.MAX_ULTIMATE_LEVEL, unlocked_ult_ranks):
            return "R"

        basic_levels = {"Q": abilities.q, "W": abilities.w, "E": abilities.e}
        for skill in self._skill_priority:
            if basic_levels.get(skill, 0) == 0:
                return skill
        for skill in self._skill_priority:
            if basic_levels.get(skill, 0) < GameRules.MAX_BASIC_ABILITY_LEVEL:
                return skill
        return None

"""Carregamento assíncrono da build com injeção nos detectores ativos."""
from __future__ import annotations

import threading
from typing import Callable

from lol_coach.domain.detectors.next_item_detector import NextItemDetector
from lol_coach.domain.detectors.skill_point_detector import SkillPointDetector
from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.domain.ports.data_dragon_repository import DataDragonRepository
from lol_coach.infrastructure.recommended_build_service import RecommendedBuildService
from lol_coach.settings.messages import LogMessages


class BuildLoader:
    """Busca a build em uma thread auxiliar e injeta nos detectores.

    Usado pela `CoachSession` assim que o nome do campeão é conhecido.
    Toda comunicação com a thread principal é feita via callbacks.
    """

    def __init__(
        self,
        build_service: RecommendedBuildService,
        data_dragon: DataDragonRepository,
    ) -> None:
        self._build_service = build_service
        self._data_dragon = data_dragon
        self._fetched_once = False

    def fetch_in_background(
        self,
        champion_name: str,
        position: str,
        on_build_loaded: Callable[[RecommendedBuild], None],
        on_log: Callable[[str], None],
        skill_detector: SkillPointDetector | None,
        next_item_detector_setter: Callable[[NextItemDetector], None] | None,
    ) -> None:
        if self._fetched_once:
            return
        self._fetched_once = True

        thread = threading.Thread(
            target=self._fetch,
            args=(
                champion_name,
                position,
                on_build_loaded,
                on_log,
                skill_detector,
                next_item_detector_setter,
            ),
            daemon=True,
        )
        thread.start()

    def _fetch(
        self,
        champion_name: str,
        position: str,
        on_build_loaded: Callable[[RecommendedBuild], None],
        on_log: Callable[[str], None],
        skill_detector: SkillPointDetector | None,
        next_item_detector_setter: Callable[[NextItemDetector], None] | None,
    ) -> None:
        try:
            build = self._build_service.fetch_for_champion(champion_name, position)
        except Exception as error:
            on_log(LogMessages.build_fetch_error(str(error)))
            return

        if build is None:
            on_log(LogMessages.build_not_found(champion_name))
            return

        on_log(LogMessages.build_loaded(build.champion, build.source))

        if skill_detector is not None:
            skill_detector.update_recommendations(
                skill_priority=build.skill_priority,
                skill_sequence=build.skill_sequence,
            )

        if next_item_detector_setter is not None and build.items_in_purchase_order():
            try:
                item_prices = self._data_dragon.get_item_prices()
            except Exception:
                item_prices = {}
            next_item_detector_setter(NextItemDetector(build, item_prices))

        on_build_loaded(build)

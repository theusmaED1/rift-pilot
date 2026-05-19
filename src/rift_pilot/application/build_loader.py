"""Carregamento assíncrono da build com injeção nos detectores ativos."""
from __future__ import annotations

import logging
import threading
from typing import Callable

from rift_pilot.domain.detectors.next_item_detector import NextItemDetector
from rift_pilot.domain.detectors.skill_point_detector import SkillPointDetector
from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository
from rift_pilot.infrastructure.recommended_build_service import RecommendedBuildService
from rift_pilot.settings.messages import LogMessages

logger = logging.getLogger(__name__)


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
        self._ai_provider = None  # Será injetado se em modo IA

    def set_ai_provider(self, provider: Any) -> None:
        """Injeta o AiBuildProvider para que possa receber dados de inimigos."""
        self._ai_provider = provider
        logger.info(f"[BuildLoader] AI provider setado: {type(provider).__name__}")

    def inject_enemies(self, lane_enemy: dict | None, full_comp: list[dict]) -> None:
        """Injeta dados de inimigos no AiBuildProvider (se aplicável)."""
        logger.info(f"[BuildLoader] inject_enemies chamado: lane_enemy={lane_enemy}, full_comp size={len(full_comp)}")
        if self._ai_provider is not None and hasattr(self._ai_provider, "set_enemies"):
            logger.info(f"[BuildLoader] Chamando set_enemies no AI provider")
            self._ai_provider.set_enemies(lane_enemy, full_comp)
        else:
            if self._ai_provider is None:
                logger.warning(f"[BuildLoader] AI provider é None, não pode injetar enemies")
            else:
                logger.warning(f"[BuildLoader] AI provider não tem método set_enemies")

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
        logger.info(f"[BuildLoader] Iniciando _fetch para {champion_name} ({position})")
        try:
            build = self._build_service.fetch_for_champion(champion_name, position)
            logger.info(f"[BuildLoader] fetch_for_champion retornou: {build}")
        except Exception as error:
            logger.error(f"[BuildLoader] Erro ao buscar build: {error}")
            on_log(LogMessages.build_fetch_error(str(error)))
            return

        if build is None:
            logger.warning(f"[BuildLoader] Build é None para {champion_name}")
            on_log(LogMessages.build_not_found(champion_name))
            return

        logger.info(f"[BuildLoader] Build carregado com sucesso: {build.champion} from {build.source}")
        on_log(LogMessages.build_loaded(build.champion, build.source))

        if skill_detector is not None:
            logger.info(f"[BuildLoader] Atualizando skill_detector com skill_priority={build.skill_priority}")
            skill_detector.update_recommendations(
                skill_priority=build.skill_priority,
                skill_sequence=build.skill_sequence,
            )

        if next_item_detector_setter is not None and build.items_in_purchase_order():
            logger.info(f"[BuildLoader] Inicializando NextItemDetector")
            try:
                item_prices = self._data_dragon.get_item_prices()
                item_sources = self._data_dragon.get_item_sources()
            except Exception as e:
                logger.warning(f"[BuildLoader] Erro ao carregar item_prices/sources: {e}")
                item_prices = {}
                item_sources = {}
            next_item_detector_setter(NextItemDetector(build, item_prices, item_sources))

        logger.info(f"[BuildLoader] Chamando on_build_loaded callback")
        on_build_loaded(build)

"""Mensagens em pt-BR usadas pelo TTS, interface gráfica e logs.

Único arquivo onde textos visíveis ao usuário podem ser definidos.
"""
from __future__ import annotations


_POSITION_NAMES_PT_BR: dict[str, str] = {
    "TOP": "top",
    "JUNGLE": "selva",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "UTILITY": "suporte",
    "NONE": "",
    "": "",
}


def translate_position(position: str) -> str:
    """Traduz o nome da posição da Live API para pt-BR usado nos anúncios."""
    return _POSITION_NAMES_PT_BR.get(position.upper(), "")


class TTSMessages:
    """Mensagens faladas pelo coach via Edge TTS."""

    @staticmethod
    def skill_point_with_recommendation(skill: str) -> str:
        return f"Skill disponível! Upa o {skill} agora!"

    @staticmethod
    def skill_point_generic() -> str:
        return "Skill disponível! Upa agora!"

    @staticmethod
    def skill_points_accumulated(count: int) -> str:
        return f"{count} pontos de skill parados! Upa logo!"

    @staticmethod
    def gold_reached_for_item(item_name: str) -> str:
        return f"Você já tem ouro para comprar {item_name}!"

    @staticmethod
    def next_item_reminder(item_name: str, can_afford: bool, missing_boots: str | None) -> str:
        if can_afford:
            base = f"Próximo item: {item_name}. Você já pode comprar!"
        else:
            base = f"Próximo item: {item_name}."
        if missing_boots:
            base += f" Botas: {missing_boots}."
        return base

    OBJECTIVE_DRAGON: dict[int, str] = {
        60: "1 minuto para o Dragão. Avise seu time!",
        30: "Dragão em 30 segundos. Avise o time!",
        10: "Dragão vai nascer em 10 segundos. Se prepara!",
    }

    OBJECTIVE_BARON: dict[int, str] = {
        60: "1 minuto para o Barão. Avise seu time!",
        30: "Barão em 30 segundos. Avise o time!",
        10: "Barão vai nascer em 10 segundos. Se prepara!",
    }

    OBJECTIVE_HERALD: dict[int, str] = {
        60: "1 minuto para o Arauto. Avise seu time!",
        30: "Arauto em 30 segundos. Avise o time!",
        10: "Arauto vai nascer em 10 segundos. Se prepara!",
    }

    TRINKET_REMINDERS: list[str] = [
        "Sua trinket está disponível! Use no mapa!",
        "Trinket parada! Vai lá usar!",
        "Você não usa sua trinket faz tempo! Coloca uma ward!",
        "Trinket disponível! Usa agora!",
    ]

    MINIMAP_REMINDERS: list[str] = [
        "Olha o minimapa!",
        "Cheque o minimapa agora!",
        "Da uma olhada no minimapa!",
        "Minimapa! Confira!",
        "Veja o minimapa!",
        "Atenção ao minimapa!",
    ]

    OBJECTIVE_VOIDGRUBS: dict[int, str] = {
        60: "1 minuto para as Larvas. Avise seu time!",
        30: "Larvas em 30 segundos. Avise o time!",
        10: "Larvas vão nascer em 10 segundos. Se prepara!",
    }

    @staticmethod
    def build_introduction(champion: str, role: str) -> str:
        if role:
            return f"{champion} no {role}."
        return f"Jogando de {champion}."

    @staticmethod
    def build_starters(starter_items: list[str]) -> str:
        return "Comece com " + " e ".join(starter_items) + "."

    @staticmethod
    def build_core(core_items: list[str]) -> str:
        return "Core: " + ", ".join(core_items) + "."

    @staticmethod
    def build_boots(boots: str) -> str:
        return f"Botas: {boots}."

    @staticmethod
    def build_max_order(skill_priority: list[str]) -> str:
        order = " depois o ".join(skill_priority)
        return f"Maximize {order}."


class UILabels:
    """Textos exibidos na interface gráfica."""

    APP_TITLE = "Rift Pilot"
    APP_SUBTITLE = "Seu coach de voz para League of Legends"

    STATUS_HEADER = "STATUS"
    STATUS_WAITING = "Aguardando o jogo iniciar..."
    STATUS_CONNECTING = "Conectando..."
    STATUS_WAITING_GAME = "Aguardando o jogo..."
    STATUS_MONITORING = "Monitorando"
    STATUS_GAME_OVER = "Jogo encerrado."

    SECTION_BUILD = "BUILD RECOMENDADA"
    SECTION_FEATURES = "AVISOS ATIVOS"
    SECTION_LOG = "LOG DE EVENTOS"

    BUTTON_START = "▶  INICIAR"
    BUTTON_STOP = "■  PARAR"
    BUTTON_CLEAR_LOG = "LIMPAR"

    BUILD_PLACEHOLDER = "—"
    BUILD_ROW_STARTERS = ("Início", "◆")
    BUILD_ROW_CORE = ("Core", "⚔")
    BUILD_ROW_BOOTS = ("Botas", "⚡")
    BUILD_ROW_SKILLS = ("Skills", "≡")
    BUILD_ROW_RUNES = ("Runas", "✦")

    FEATURE_SKILL_TITLE = "Pontos de skill disponíveis"
    FEATURE_SKILL_DESCRIPTION = "Avisa quando você sobe de nível e tem skill para evoluir"
    FEATURE_SKILL_ICON = "✦"

    FEATURE_OBJECTIVES_TITLE = "Objetivos (Dragão, Barão, Arauto, Larvas)"
    FEATURE_OBJECTIVES_DESCRIPTION = "Anuncia o spawn e o status dos objetivos do mapa"
    FEATURE_OBJECTIVES_ICON = "♛"

    FEATURE_BUILD_ANNOUNCE_TITLE = "Anunciar build no início da partida"
    FEATURE_BUILD_ANNOUNCE_DESCRIPTION = "Lê em voz alta a build recomendada quando o jogo começa"
    FEATURE_BUILD_ANNOUNCE_ICON = "►"

    FEATURE_NEXT_ITEM_TITLE = "Lembrete do próximo item da build"
    FEATURE_NEXT_ITEM_DESCRIPTION = "Toca um aviso quando você tem ouro para o próximo item"
    FEATURE_NEXT_ITEM_ICON = "●"

    FEATURE_MINIMAP_TITLE = "Lembrete do minimapa"
    FEATURE_MINIMAP_DESCRIPTION = "Avisa periodicamente para checar o minimapa"
    FEATURE_MINIMAP_ICON = "◎"

    FEATURE_TRINKET_TITLE = "Lembrete de trinket"
    FEATURE_TRINKET_DESCRIPTION = "Avisa quando sua trinket está disponível há mais de 1 minuto"
    FEATURE_TRINKET_ICON = "◈"

    FOOTER_TTS_INFO = "◄)) EDGE TTS — PT-BR-ANTONIONEURAL"

    CLI_DESCRIPTION = "Rift Pilot — modo CLI (replay e testes)"
    CLI_REPLAY_HELP = "Arquivo .jsonl gerado por scripts/log_game.py"
    CLI_VOICE_HELP = "Voz Edge TTS (padrão: pt-BR-AntonioNeural)"


class LogMessages:
    """Mensagens estruturadas exibidas no painel de log e na CLI."""

    APP_INITIALIZED = "Aplicação inicializada com sucesso."
    TTS_LOADED = "Módulo TTS: AntonioNeural (pt-BR) carregado."
    WAITING_USER_START = "Aguardando comando para iniciar a sessão."
    GAME_CONNECTED = "● Conectado ao jogo!"
    GAME_ENDED = "— Jogo encerrado."
    CLI_MONITORING = "Monitorando... (Ctrl+C para parar)"
    CLI_STOPPED_BY_USER = "Encerrado."

    @staticmethod
    def build_loaded(champion: str, source: str) -> str:
        return f"✓ Build de {champion} carregada (fonte: {source})"

    @staticmethod
    def build_not_found(champion: str) -> str:
        return f"× Build não encontrada para {champion}"

    @staticmethod
    def build_fetch_error(error: str) -> str:
        return f"× Erro ao buscar build: {error}"

    @staticmethod
    def coach_event(game_time_seconds: float, message: str) -> str:
        return f"[{game_time_seconds:.0f}s] {message}"

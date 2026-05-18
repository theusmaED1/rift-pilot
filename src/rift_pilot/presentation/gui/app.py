"""Janela principal: orquestra as views e dispara a `CoachSession` em thread."""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path

from rift_pilot.application.build_loader import BuildLoader
from rift_pilot.application.coach_session import (
    CoachSession,
    SessionCallbacks,
    SessionStatus,
)
from rift_pilot.application.session_options import SessionOptions
from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.infrastructure.build_providers.ai_build_provider import (
    AiBuildProvider,
)
from rift_pilot.infrastructure.build_providers.ai_message_provider import (
    AiMessageProvider,
)
from rift_pilot.infrastructure.groq.router import GroqRouter
from rift_pilot.infrastructure.groq.token_logger import TokenLogger
from rift_pilot.infrastructure.opgg_mcp.client import OpggMcpClient
from rift_pilot.infrastructure.recommended_build_service import RecommendedBuildService
from rift_pilot.infrastructure.riot.data_dragon_client import DataDragonClient
from rift_pilot.infrastructure.riot.live_client_data_api import LiveClientDataApi
from rift_pilot.infrastructure.secrets.keyring_store import (
    load_groq_key,
    save_groq_key,
)
from rift_pilot.infrastructure.tts.edge_tts_speaker import EdgeTtsSpeaker
from rift_pilot.infrastructure.tts.speech_priority_queue import SpeechPriorityQueue
from rift_pilot.presentation.gui.theme import Colors, Dimensions, Fonts
from rift_pilot.presentation.gui.views import BuildView, FeaturesView, LogView, StatusView
from rift_pilot.presentation.gui.views.features_view import FeatureToggles
from rift_pilot.presentation.gui.widgets import horizontal_separator
from rift_pilot.settings.config_loader import AppConfig, load_app_config
from rift_pilot.settings.constants import Timing
from rift_pilot.settings.messages import LogMessages, UILabels


class CoachApp(tk.Tk):
    """Aplicação Tkinter — janela única dividida em 4 cards + botão."""

    def __init__(self) -> None:
        super().__init__()
        self.title(UILabels.APP_TITLE)
        self.resizable(False, False)
        self.configure(bg=Colors.BACKGROUND_PRIMARY)
        self._set_window_icon()

        self._config: AppConfig = load_app_config()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._stop_signal = threading.Event()
        self._session_thread: threading.Thread | None = None

        # Foco temporário: só "build IA" e "farm" durante a refatoração do modo IA.
        # Outras features ficam desativadas até a integração progressiva (slots
        # 4, 5, 6 + lembretes IA) ser finalizada.
        self._toggles = FeatureToggles(
            skill_points=tk.BooleanVar(value=False),
            objectives=tk.BooleanVar(value=False),
            build_announce=tk.BooleanVar(value=True),
            next_item=tk.BooleanVar(value=True),
            minimap=tk.BooleanVar(value=False),
            trinket=tk.BooleanVar(value=False),
            farm=tk.BooleanVar(value=True),
            ai_build=tk.BooleanVar(value=True),
        )

        self._tone_var = tk.StringVar(value=UILabels.CONFIG_TONE_NEUTRAL)
        self._mode_var = tk.StringVar(value=UILabels.CONFIG_MODE_SIMPLE)
        # Carrega chave Groq do keyring (Windows Credential Manager) — fica
        # mascarada no campo. Usuário cola uma vez, app lembra dali em diante.
        self._groq_key_var = tk.StringVar(value=load_groq_key())
        self._saved_groq_key = self._groq_key_var.get()

        self._build_ui()
        self._poll_log_queue()

        for message in (
            LogMessages.APP_INITIALIZED,
            LogMessages.TTS_LOADED,
            LogMessages.WAITING_USER_START,
        ):
            self._log_view.append(message)

    # ── Construção da UI ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._build_header()
        horizontal_separator(self)
        self._status_view = StatusView(self)

        content = tk.Frame(self, bg=Colors.BACKGROUND_PRIMARY)
        content.pack(fill="x")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(2, weight=1)

        left = tk.Frame(content, bg=Colors.BACKGROUND_PRIMARY)
        left.grid(row=0, column=0, sticky="nsew")

        tk.Frame(content, bg=Colors.BORDER, width=1).grid(row=0, column=1, sticky="ns")

        right = tk.Frame(content, bg=Colors.BACKGROUND_PRIMARY)
        right.grid(row=0, column=2, sticky="nsew")

        self._build_view = BuildView(left)
        FeaturesView(right, self._toggles)
        self._build_coach_config(right)

        self._build_action_button()
        self._log_view = LogView(self)
        self._build_footer()
        self.geometry(Dimensions.WINDOW_GEOMETRY)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=Colors.BACKGROUND_PRIMARY, pady=16)
        header.pack(fill="x")
        tk.Label(
            header, text=UILabels.APP_TITLE,
            font=Fonts.TITLE,
            fg=Colors.GOLD, bg=Colors.BACKGROUND_PRIMARY,
        ).pack()
        tk.Label(
            header, text=UILabels.APP_SUBTITLE,
            font=Fonts.SUBTITLE,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(pady=(2, 0))

    def _build_action_button(self) -> None:
        outer = tk.Frame(self, bg=Colors.BACKGROUND_PRIMARY, pady=14)
        outer.pack(fill="x")
        btn_frame = tk.Frame(outer, bg=Colors.GOLD, height=Dimensions.BUTTON_HEIGHT)
        btn_frame.pack(fill="x", padx=60)
        btn_frame.pack_propagate(False)
        self._action_button = tk.Button(
            btn_frame, text=UILabels.BUTTON_START,
            font=Fonts.BUTTON_PRIMARY,
            fg=Colors.BACKGROUND_PRIMARY, bg=Colors.GOLD,
            activebackground=Colors.GOLD_DIM,
            relief="flat", cursor="hand2", bd=0,
            command=self._toggle_session,
        )
        self._action_button.pack(fill="both", expand=True)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=Colors.BACKGROUND_PRIMARY, pady=8)
        footer.pack(fill="x")
        tk.Label(
            footer, text=UILabels.FOOTER_TTS_INFO,
            font=Fonts.FOOTER,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(side="left", padx=16)
        tk.Label(
            footer, text="v1.0",
            font=Fonts.FOOTER,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(side="right", padx=16)

    def _build_coach_config(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent, bg=Colors.BACKGROUND_PRIMARY, padx=12)
        outer.pack(fill="x", pady=(10, 4))

        tk.Label(
            outer, text=UILabels.SECTION_COACH_CONFIG,
            font=Fonts.SECTION_HEADER,
            fg=Colors.GOLD_DIM, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        card = tk.Frame(outer, bg=Colors.BACKGROUND_CARD)
        card.pack(fill="x")

        tone_row = tk.Frame(card, bg=Colors.BACKGROUND_CARD)
        tone_row.pack(fill="x", padx=12, pady=8)
        tk.Label(
            tone_row, text=UILabels.CONFIG_TONE_LABEL,
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
        ).pack(side="left")
        tone_menu = tk.OptionMenu(
            tone_row, self._tone_var,
            UILabels.CONFIG_TONE_NEUTRAL,
            UILabels.CONFIG_TONE_FUNNY,
            UILabels.CONFIG_TONE_SERIOUS,
            UILabels.CONFIG_TONE_TRYHARD,
            UILabels.CONFIG_TONE_SARCASTIC,
        )
        tone_menu.config(
            bg=Colors.BACKGROUND_CARD, fg=Colors.TEXT_PRIMARY,
            activebackground=Colors.GOLD_DIM, activeforeground=Colors.TEXT_PRIMARY,
            relief="solid", bd=1,
        )
        tone_menu["menu"].config(bg=Colors.BACKGROUND_CARD, fg=Colors.TEXT_PRIMARY)
        tone_menu.pack(side="right")

        tk.Frame(card, bg=Colors.BORDER, height=1).pack(fill="x")

        mode_row = tk.Frame(card, bg=Colors.BACKGROUND_CARD)
        mode_row.pack(fill="x", padx=12, pady=8)
        tk.Label(
            mode_row, text=UILabels.CONFIG_MODE_LABEL,
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
        ).pack(side="left")
        mode_menu = tk.OptionMenu(
            mode_row, self._mode_var,
            UILabels.CONFIG_MODE_SIMPLE,
            UILabels.CONFIG_MODE_EXPLANATORY,
        )
        mode_menu.config(
            bg=Colors.BACKGROUND_CARD, fg=Colors.TEXT_PRIMARY,
            activebackground=Colors.GOLD_DIM, activeforeground=Colors.TEXT_PRIMARY,
            relief="solid", bd=1,
        )
        mode_menu["menu"].config(bg=Colors.BACKGROUND_CARD, fg=Colors.TEXT_PRIMARY)
        mode_menu.pack(side="right")

        tk.Frame(card, bg=Colors.BORDER, height=1).pack(fill="x")

        key_row = tk.Frame(card, bg=Colors.BACKGROUND_CARD)
        key_row.pack(fill="x", padx=12, pady=8)
        tk.Label(
            key_row, text="Chave Groq",
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
        ).pack(side="left")

        # Botão de limpar (remove do keyring)
        clear_button = tk.Button(
            key_row, text="Limpar",
            font=Fonts.FOOTER,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_CARD,
            activebackground=Colors.ACCENT_RED_PRESSED,
            relief="flat", cursor="hand2", bd=0,
            command=self._clear_groq_key,
        )
        clear_button.pack(side="right", padx=(4, 0))

        key_entry = tk.Entry(
            key_row, textvariable=self._groq_key_var,
            bg=Colors.BACKGROUND_CARD, fg=Colors.TEXT_PRIMARY,
            insertbackground=Colors.TEXT_PRIMARY,
            relief="solid", bd=1, width=26, show="*",
        )
        key_entry.pack(side="right", padx=(8, 0))

        # Indicador visual de "chave salva"
        if self._saved_groq_key:
            tk.Label(
                key_row, text="✓",
                font=Fonts.BODY_LABEL,
                fg=Colors.ACCENT_GREEN, bg=Colors.BACKGROUND_CARD,
            ).pack(side="right", padx=(4, 0))

    def _clear_groq_key(self) -> None:
        """Remove chave do keyring e limpa o campo."""
        save_groq_key("")
        self._groq_key_var.set("")
        self._saved_groq_key = ""

    def _set_window_icon(self) -> None:
        icon_path = Path("icon.ico")
        if not icon_path.exists():
            icon_path = Path(getattr(sys, "_MEIPASS", ".")) / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    # ── Ciclo da sessão ──────────────────────────────────────────────────────

    def _toggle_session(self) -> None:
        if self._session_thread and self._session_thread.is_alive():
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self) -> None:
        self._stop_signal.clear()
        self._action_button.config(
            text=UILabels.BUTTON_STOP,
            bg=Colors.ACCENT_RED,
            activebackground=Colors.ACCENT_RED_PRESSED,
        )
        self._status_view.set(UILabels.STATUS_CONNECTING, Colors.GOLD)
        self._build_view.reset()

        self._session_thread = threading.Thread(target=self._run_session, daemon=True)
        self._session_thread.start()

    def _stop_session(self) -> None:
        self._stop_signal.set()
        self._action_button.config(
            text=UILabels.BUTTON_START,
            bg=Colors.GOLD,
            activebackground=Colors.GOLD_DIM,
        )
        self._status_view.set(UILabels.STATUS_WAITING, Colors.TEXT_DIMMED)
        self._build_view.reset()

    def _run_session(self) -> None:
        data_dragon = DataDragonClient()
        options = self._current_session_options()

        # Persistir chave Groq no keyring se mudou
        current_key = self._groq_key_var.get().strip()
        if current_key and current_key != self._saved_groq_key:
            save_groq_key(current_key)
            self._saved_groq_key = current_key

        if not current_key:
            self._log_queue.put(
                "⚠ Chave Groq não configurada. Cole sua chave no campo acima "
                "antes de iniciar."
            )
            self._handle_status_change(SessionStatus.GAME_ENDED)
            return

        # TokenLogger compartilhado entre router e CoachSession
        recordings_dir = Path("recordings")
        token_logger = TokenLogger(recordings_dir)

        groq_router = GroqRouter(api_key=current_key, token_logger=token_logger)
        mcp_client = OpggMcpClient()

        build_provider = AiBuildProvider(
            mcp_client=mcp_client,
            data_dragon=data_dragon,
            groq_router=groq_router,
            tone=options.tone,
            mode=options.mode,
        )

        # Message provider gera lembretes/farm via IA (gpt-oss-20b).
        # Compartilha o mesmo router (e seus contadores de TPD) com o build provider.
        message_provider = AiMessageProvider(
            groq_router=groq_router, tone=options.tone
        )

        build_loader = BuildLoader(
            build_service=RecommendedBuildService(
                build_provider=build_provider,
                data_dragon=data_dragon,
            ),
            data_dragon=data_dragon,
            message_provider=message_provider,
        )
        build_loader.set_ai_provider(build_provider)

        speaker = EdgeTtsSpeaker()
        speech_queue = SpeechPriorityQueue(
            speaker=speaker, min_gap_seconds=self._config.speaker.min_gap_seconds
        )

        session = CoachSession(
            data_source=LiveClientDataApi(),
            speech_queue=speech_queue,
            build_loader=build_loader,
            options=options,
            callbacks=SessionCallbacks(
                on_status_change=self._handle_status_change,
                on_log_message=self._log_queue.put,
                on_build_loaded=self._handle_build_loaded,
            ),
            poll_interval_seconds=self._config.api.poll_interval_seconds,
            warn_offsets_seconds=self._config.objectives.warn_seconds,
            token_logger=token_logger,
            message_provider=message_provider,
        )
        session.run(self._stop_signal)

    def _current_session_options(self) -> SessionOptions:
        tone_label = self._tone_var.get()
        tone_map = {
            UILabels.CONFIG_TONE_NEUTRAL: "neutral",
            UILabels.CONFIG_TONE_FUNNY: "funny",
            UILabels.CONFIG_TONE_SERIOUS: "serious",
            UILabels.CONFIG_TONE_TRYHARD: "tryhard",
            UILabels.CONFIG_TONE_SARCASTIC: "sarcastic",
        }
        tone = tone_map.get(tone_label, "neutral")

        mode_label = self._mode_var.get()
        mode_map = {
            UILabels.CONFIG_MODE_SIMPLE: "simple",
            UILabels.CONFIG_MODE_EXPLANATORY: "explanatory",
        }
        mode = mode_map.get(mode_label, "simple")

        return SessionOptions(
            skill_points=self._toggles.skill_points.get(),
            objectives=self._toggles.objectives.get(),
            build_announce=self._toggles.build_announce.get(),
            next_item=self._toggles.next_item.get(),
            minimap=self._toggles.minimap.get(),
            trinket=self._toggles.trinket.get(),
            farm=self._toggles.farm.get(),
            tone=tone,
            mode=mode,
            use_ai_build=self._toggles.ai_build.get(),
        )

    # ── Callbacks vindos da thread da sessão ─────────────────────────────────

    def _handle_status_change(self, status: SessionStatus) -> None:
        text, color = _STATUS_PRESENTATION[status]
        self.after(0, lambda: self._status_view.set(text, color))
        if status == SessionStatus.GAME_ENDED:
            self.after(0, self._stop_session)

    def _handle_build_loaded(self, build: RecommendedBuild) -> None:
        self.after(0, lambda: self._build_view.display(build))

    # ── Polling do log ───────────────────────────────────────────────────────

    def _poll_log_queue(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                self._log_view.append(message)
        except queue.Empty:
            pass
        self.after(Timing.LOG_POLL_INTERVAL_MS, self._poll_log_queue)

    def on_close(self) -> None:
        self._stop_signal.set()
        self.destroy()


_STATUS_PRESENTATION: dict[SessionStatus, tuple[str, str]] = {
    SessionStatus.CONNECTING: (UILabels.STATUS_CONNECTING, Colors.GOLD),
    SessionStatus.WAITING_FOR_GAME: (UILabels.STATUS_WAITING_GAME, Colors.TEXT_DIMMED),
    SessionStatus.LOADING_SCREEN: (UILabels.STATUS_LOADING_SCREEN, Colors.GOLD),
    SessionStatus.MONITORING: (UILabels.STATUS_MONITORING, Colors.ACCENT_GREEN),
    SessionStatus.GAME_ENDED: (UILabels.STATUS_GAME_OVER, Colors.TEXT_DIMMED),
}


def run_app() -> None:
    app = CoachApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

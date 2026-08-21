import sys
import asyncio
import psutil
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QFrame, QSplitter
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from ui.arc_reactor import ArcReactorWidget
from core.stt_engine import STTEngine
from core.tts_engine import TTSEngine
from core.voice_pipeline import VoicePipeline
from core.action_engine import ActionEngine
from core.audio_engine import AudioEngine
from core.memory_engine import MemoryEngine


class VoicePipelineThread(QThread):
    """Background Async Thread running Duplex Audio Engine & Voice Pipeline without freezing PyQt GUI."""

    status_changed = pyqtSignal(str)
    user_transcribed = pyqtSignal(str)
    jarvis_chunk_emitted = pyqtSignal(str)
    jarvis_speaking_finished = pyqtSignal()
    audio_level_emitted = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stt = STTEngine(model_size="base")
        self.tts = TTSEngine()
        self.action_engine = ActionEngine()
        self.pipeline = VoicePipeline(stt_engine=self.stt, tts_engine=self.tts, action_engine=self.action_engine)
        self.audio_engine = AudioEngine(self.stt, self.tts)
        self.memory_engine = MemoryEngine()

        self.audio_engine.set_audio_level_callback(lambda level: self.audio_level_emitted.emit(level))

        self.is_running = True
        self.mic_enabled = True
        self.pending_query = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main_loop())

    @property
    def is_mic_active(self) -> bool:
        """Single Source of Truth for Microphone Hardware & Mute State."""
        mic_online = getattr(self.stt, 'input_device_index', None) is not None
        return self.mic_enabled and mic_online

    async def _main_loop(self):
        self.status_changed.emit("STANDBY")
        while self.is_running:
            if self.pending_query:
                query = self.pending_query
                self.pending_query = None
                await self._process_text_query(query)
            elif self.is_mic_active:
                try:
                    self.status_changed.emit("LISTENING")
                    detected, spoken_text = await self.audio_engine.listen_for_command()
                    if detected and self.is_mic_active:
                        if spoken_text:
                            await self._process_text_query(spoken_text)
                    else:
                        await asyncio.sleep(0.05)
                except Exception as e:
                    await asyncio.sleep(0.2)
            else:
                self.status_changed.emit("STANDBY")
                await asyncio.sleep(0.1)

    def submit_query(self, query: str):
        """Submit text command from HUD input field."""
        self.pending_query = query

    def halt_override(self):
        """Emergency HALT: interrupts speech and flushes audio buffers immediately."""
        self.audio_engine.interrupt_speech()
        self.status_changed.emit("STANDBY")

    async def _process_text_query(self, query: str):
        try:
            self.status_changed.emit("THINKING")
            self.user_transcribed.emit(query)

            req_id_container = ["REQ-000000"]

            def _hud_stage_callback(stage: str, msg: str):
                if stage == "REQ_ID":
                    req_id_container[0] = msg
                    return
                # Instantly transition status based on active planner stage
                if stage in ("PLAN", "EXECUTION"):
                    self.status_changed.emit("PROCESSING")
                elif stage == "VERIFICATION":
                    self.status_changed.emit("SPEAKING")
                formatted = f"[{req_id_container[0]}][{stage}] {msg}"
                self.jarvis_chunk_emitted.emit(formatted)

            # Single Output Path: Pass speak_audio=False so process_user_input does NOT speak twice
            reply = await self.pipeline.process_user_input(query, chunk_callback=_hud_stage_callback, speak_audio=False)

            self.jarvis_chunk_emitted.emit(f"[{req_id_container[0]}][RESPONSE] {reply}")
            self.status_changed.emit("SPEAKING")

            # Single Authoritative Audio Path
            self.jarvis_chunk_emitted.emit(f"[{req_id_container[0]}][TTS] START")
            await self.audio_engine.speak_text_async(reply)
            self.jarvis_chunk_emitted.emit(f"[{req_id_container[0]}][TTS] END")
            self.jarvis_speaking_finished.emit()

        except Exception as e:
            err_msg = f"[ERROR]: Processing request failed: {str(e)}"
            self.jarvis_chunk_emitted.emit(err_msg)
        finally:
            self.status_changed.emit("LISTENING" if self.is_mic_active else "STANDBY")





class JarvisHUDWindow(QMainWindow):
    """Iron Man Stark HUD Window with 75%/25% Viewport Inversion, QComboBox Model Selector, Dynamic Arc Reactor State Colors, Hardware Telemetry, and Emergency HALT Override."""

    STATUS_STYLES = {
        "STANDBY": ("#00F0FF", "rgba(0, 240, 255, 0.1)"),
        "LISTENING": ("#00FF88", "rgba(0, 255, 136, 0.15)"),
        "THINKING": ("#FFB300", "rgba(255, 179, 0, 0.15)"),
        "PROCESSING": ("#FFB300", "rgba(255, 179, 0, 0.15)"),
        "SPEAKING": ("#00E5FF", "rgba(0, 229, 255, 0.2)")
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("STARK INDUSTRIES — JARVIS AI WORKSTATION")
        self.resize(1100, 750)

        self._setup_dark_theme()
        self._init_ui()

        # Start Voice Pipeline & Hardware Telemetry Timers
        self.pipeline_thread = VoicePipelineThread(self)
        self.pipeline_thread.status_changed.connect(self._on_status_changed)
        self.pipeline_thread.user_transcribed.connect(self._on_user_transcribed)
        self.pipeline_thread.jarvis_chunk_emitted.connect(self._on_jarvis_chunk)
        self.pipeline_thread.audio_level_emitted.connect(self._on_audio_level)
        self.pipeline_thread.start()

        # Sync model dropdown with LLMManager active model at startup
        if hasattr(self.pipeline_thread, 'pipeline') and hasattr(self.pipeline_thread.pipeline, 'llm'):
            active_model = getattr(self.pipeline_thread.pipeline.llm, 'model_name', 'jarvis-trained-model')
            index = self.model_selector.findText(active_model)
            if index != -1:
                self.model_selector.setCurrentIndex(index)

        self.telemetry_timer = QTimer(self)

        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(1000)

    def _setup_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(5, 10, 20))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 230, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(10, 18, 32))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 230, 255))
        self.setPalette(palette)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---------------- TOP TELEMETRY & HEADER BAR ----------------
        top_bar = QHBoxLayout()

        self.status_label = QLabel("STATUS: STANDBY", self)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #00f0ff; padding: 4px 10px; background: rgba(0, 240, 255, 0.1); border: 1px solid #00f0ff; border-radius: 4px;")
        top_bar.addWidget(self.status_label)

        top_bar.addStretch()

        # Restored Model Selector Dropdown
        model_label = QLabel("MODEL:", self)
        model_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        model_label.setStyleSheet("color: #00e6ff; margin-left: 8px;")
        top_bar.addWidget(model_label)

        self.model_selector = QComboBox(self)
        self.model_selector.setFont(QFont("Consolas", 10))
        self.model_selector.setStyleSheet("""
            QComboBox {
                background: rgba(10, 20, 36, 0.9);
                color: #00f0ff;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #0a1424;
                color: #00f0ff;
                selection-background-color: #00e6ff;
                selection-color: #000000;
            }
        """)

        # Exclusively use fine-tuned jarvis-trained-model
        self.model_selector.addItems([
            "jarvis-trained-model"
        ])
        self.model_selector.currentTextChanged.connect(self._on_model_changed)
        top_bar.addWidget(self.model_selector)

        self.telemetry_label = QLabel("CPU: 0% | RAM: 0% | SYS: OK", self)
        self.telemetry_label.setFont(QFont("Consolas", 10))
        self.telemetry_label.setStyleSheet("color: #00b8ff; padding: 4px 10px;")
        top_bar.addWidget(self.telemetry_label)

        # Emergency HALT / OVERRIDE Button
        self.halt_btn = QPushButton("HALT / OVERRIDE", self)
        self.halt_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.halt_btn.setStyleSheet("""
            QPushButton {
                color: #ff3344;
                background: rgba(255, 51, 68, 0.15);
                border: 2px solid #ff3344;
                border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: rgba(255, 51, 68, 0.4);
                color: #ffffff;
            }
        """)
        self.halt_btn.clicked.connect(self._on_halt_clicked)
        top_bar.addWidget(self.halt_btn)

        # Mic Toggle Button
        self.mic_btn = QPushButton("MIC: ONLINE", self)
        self.mic_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.mic_btn.setStyleSheet("""
            QPushButton {
                color: #00ff88;
                background: rgba(0, 255, 136, 0.15);
                border: 1px solid #00ff88;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: rgba(0, 255, 136, 0.3);
            }
        """)
        self.mic_btn.clicked.connect(self._toggle_mic)
        top_bar.addWidget(self.mic_btn)

        main_layout.addLayout(top_bar)

        # ---------------- VIEWPORT INVERSION SPLITTER (75% / 25%) ----------------
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Upper Area (75%): Audio-Reactive Arc Reactor Visualizer Canvas
        self.reactor = ArcReactorWidget(self)
        splitter.addWidget(self.reactor)

        # Lower Area (25%): Sleek Console Log & Input Field
        bottom_widget = QWidget(self)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.console_log = QTextEdit(self)
        self.console_log.setReadOnly(True)
        self.console_log.setFont(QFont("Consolas", 10))
        self.console_log.setStyleSheet("""
            QTextEdit {
                background-color: rgba(6, 14, 28, 0.9);
                color: #00e6ff;
                border: 1px solid rgba(0, 230, 255, 0.3);
                border-radius: 4px;
                padding: 6px;
            }
        """)
        bottom_layout.addWidget(self.console_log)

        # Command Input Field
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Enter command or question, sir...")
        self.input_field.setFont(QFont("Consolas", 10))
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(10, 20, 36, 0.9);
                color: #00e6ff;
                border: 1px solid #00e6ff;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.input_field.returnPressed.connect(self._send_text_command)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("EXECUTE", self)
        self.send_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 230, 255, 0.2);
                color: #00e6ff;
                border: 1px solid #00e6ff;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 255, 0.4);
            }
        """)
        self.send_btn.clicked.connect(self._send_text_command)
        input_layout.addWidget(self.send_btn)

        bottom_layout.addLayout(input_layout)
        splitter.addWidget(bottom_widget)

        # Apply 75% / 25% ratio
        splitter.setSizes([550, 180])
        main_layout.addWidget(splitter)

        self._log_system("STARK INDUSTRIES JARVIS Workstation Online. All systems nominal.")

    def _update_telemetry(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.telemetry_label.setText(f"CPU: {cpu}% | RAM: {ram}% | SYS: ONLINE")

    def _on_model_changed(self, model_name: str):
        """Updates active Ollama model in LLMManager and logs switch to console."""
        if hasattr(self, 'pipeline_thread') and hasattr(self.pipeline_thread.pipeline, 'llm'):
            self.pipeline_thread.pipeline.llm.set_model(model_name)
            self._log_system(f"LLM Engine switched to '{model_name}'.")

    def _toggle_mic(self):
        self.pipeline_thread.mic_enabled = not self.pipeline_thread.mic_enabled
        if self.pipeline_thread.mic_enabled:
            self.mic_btn.setText("MIC: ONLINE")
            self.mic_btn.setStyleSheet("color: #00ff88; background: rgba(0, 255, 136, 0.15); border: 1px solid #00ff88;")
            self._log_system("Microphone listening ENABLED.")
        else:
            self.mic_btn.setText("MIC: OFFLINE")
            self.mic_btn.setStyleSheet("color: #ff3344; background: rgba(255, 51, 68, 0.15); border: 1px solid #ff3344;")
            self._log_system("Microphone listening MUTED.")

    def _on_halt_clicked(self):
        self.pipeline_thread.halt_override()
        self.reactor.set_audio_level(0.0)
        self._log_system("EMERGENCY HALT OVERRIDE: Flushed speech and action queues.")

    def _send_text_command(self):
        cmd = self.input_field.text().strip()
        if cmd:
            self.input_field.clear()
            self.pipeline_thread.submit_query(cmd)

    def _on_status_changed(self, status: str):
        status_upper = status.upper().strip()
        self.status_label.setText(f"STATUS: {status_upper}")
        self.reactor.set_state(status_upper)

        color, bg = self.STATUS_STYLES.get(status_upper, ("#00F0FF", "rgba(0, 240, 255, 0.1)"))
        self.status_label.setStyleSheet(f"color: {color}; padding: 4px 10px; background: {bg}; border: 1px solid {color}; border-radius: 4px;")

    def _on_user_transcribed(self, text: str):
        self.console_log.append(f"<font color='#00ffaa'><b>[USER]:</b> {text}</font>")

    def _on_jarvis_chunk(self, text: str):
        self.console_log.append(f"<font color='#00e6ff'><b>[JARVIS]:</b> {text}</font>")

    def _on_audio_level(self, level: float):
        self.reactor.set_audio_level(level)

    def _log_system(self, message: str):
        self.console_log.append(f"<font color='#ffb700'><b>[SYSTEM]:</b> {message}</font>")

    def closeEvent(self, event):
        self.pipeline_thread.is_running = False
        self.pipeline_thread.quit()
        event.accept()

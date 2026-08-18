import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush

class ArcReactorWidget(QWidget):
    """Audio-Reactive Stark Arc Reactor Canvas featuring dynamic RGB state color transitions (STANDBY, LISTENING, THINKING, SPEAKING)."""

    COLOR_MAP = {
        "STANDBY": {
            "primary": QColor("#00F0FF"),
            "secondary": QColor("#00A3E0"),
            "glow": (0, 240, 255, 75),
            "speed": 1.0
        },
        "LISTENING": {
            "primary": QColor("#00FF88"),
            "secondary": QColor("#00CC66"),
            "glow": (0, 255, 136, 100),
            "speed": 2.5
        },
        "THINKING": {
            "primary": QColor("#FFB300"),
            "secondary": QColor("#FF8800"),
            "glow": (255, 179, 0, 120),
            "speed": 4.0
        },
        "PROCESSING": {
            "primary": QColor("#FFB300"),
            "secondary": QColor("#FF8800"),
            "glow": (255, 179, 0, 120),
            "speed": 4.0
        },
        "SPEAKING": {
            "primary": QColor("#00E5FF"),
            "secondary": QColor("#FFE500"),
            "glow": (0, 229, 255, 150),
            "speed": 3.0
        }
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle_outer = 0.0
        self.angle_inner = 0.0
        self.pulse_phase = 0.0
        self.audio_level = 0.0  # Normalized 0.0 to 1.0 energy level

        self.current_state = "STANDBY"
        self.curr_primary = QColor("#00F0FF")
        self.curr_secondary = QColor("#00A3E0")
        self.target_primary = QColor("#00F0FF")
        self.target_secondary = QColor("#00A3E0")
        self.rotation_speed = 1.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)  # ~60 FPS animation

    def set_state(self, state: str):
        """Updates target state color palette and rotation speed."""
        state_upper = state.upper().strip()
        self.current_state = state_upper

        palette = self.COLOR_MAP.get(state_upper, self.COLOR_MAP["STANDBY"])
        self.target_primary = palette["primary"]
        self.target_secondary = palette["secondary"]
        self.rotation_speed = palette["speed"]

    def set_audio_level(self, level: float):
        """Sets live decibel energy level for dynamic visualizer scaling."""
        self.audio_level = max(0.0, min(1.0, level))

    def _lerp_color(self, curr: QColor, target: QColor, factor: float = 0.08) -> QColor:
        r = int(curr.red() + (target.red() - curr.red()) * factor)
        g = int(curr.green() + (target.green() - curr.green()) * factor)
        b = int(curr.blue() + (target.blue() - curr.blue()) * factor)
        a = int(curr.alpha() + (target.alpha() - curr.alpha()) * factor)
        return QColor(r, g, b, a)

    def _animate(self):
        # Fluid color interpolation between current and target colors
        self.curr_primary = self._lerp_color(self.curr_primary, self.target_primary, 0.08)
        self.curr_secondary = self._lerp_color(self.curr_secondary, self.target_secondary, 0.08)

        base_speed_outer = 0.8 * self.rotation_speed
        base_speed_inner = -1.2 * self.rotation_speed
        audio_boost = self.audio_level * 3.5

        self.angle_outer = (self.angle_outer + base_speed_outer + audio_boost) % 360
        self.angle_inner = (self.angle_inner + base_speed_inner - audio_boost) % 360
        self.pulse_phase = (self.pulse_phase + 0.05 + self.audio_level * 0.15) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        cx, cy = width / 2.0, height / 2.0
        base_radius = min(width, height) * 0.30

        # Audio-reactive pulse & glow radius scaling
        pulse_scale = 1.0 + 0.05 * math.sin(self.pulse_phase) + (self.audio_level * 0.15)
        core_radius = base_radius * pulse_scale

        palette = self.COLOR_MAP.get(self.current_state, self.COLOR_MAP["STANDBY"])
        gr, gg, gb, ga = palette["glow"]

        # Background radial glow
        grad = QRadialGradient(cx, cy, core_radius * 1.8)
        glow_alpha = int(ga + 80 * self.audio_level)
        grad.setColorAt(0.0, QColor(gr, gg, gb, min(255, glow_alpha)))
        grad.setColorAt(0.4, QColor(gr, gg, gb, int(glow_alpha * 0.4)))
        grad.setColorAt(1.0, QColor(5, 12, 24, 0))
        painter.fillRect(self.rect(), QBrush(grad))

        # 1. Outer Rotating Segmented Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_outer)

        pen_outer = QPen(self.curr_primary, 4)
        painter.setPen(pen_outer)
        r_outer = core_radius * 1.25
        for i in range(12):
            painter.drawArc(int(-r_outer), int(-r_outer), int(2*r_outer), int(2*r_outer), i * 30 * 16, 20 * 16)
        painter.restore()

        # 2. Inner Reverse Segmented Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_inner)

        pen_inner = QPen(self.curr_secondary, 3)
        painter.setPen(pen_inner)
        r_inner = core_radius * 0.85
        for i in range(8):
            painter.drawArc(int(-r_inner), int(-r_inner), int(2*r_inner), int(2*r_inner), i * 45 * 16, 30 * 16)
        painter.restore()

        # 3. Central Core & Glowing Energy Center
        painter.setPen(Qt.PenStyle.NoPen)
        core_color = QColor(self.curr_primary.red(), self.curr_primary.green(), self.curr_primary.blue(), 230)
        painter.setBrush(QBrush(core_color))
        painter.drawEllipse(QPointF(cx, cy), core_radius * 0.45, core_radius * 0.45)

        # Audio Waveform Pulse Rings
        if self.audio_level > 0.05:
            wave_pen = QPen(self.curr_primary, 2)
            painter.setPen(wave_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r_wave = core_radius * (1.1 + 0.3 * self.audio_level)
            painter.drawEllipse(QPointF(cx, cy), r_wave, r_wave)

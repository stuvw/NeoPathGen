# ══════════════════════════════════════════════════════════════════════════════
# Stage 4 panel
# ══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QToolBar, QStatusBar,
    QSizePolicy, QGroupBox, QTabWidget, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QFileDialog,
    QMessageBox, QAbstractItemView, QScrollArea, QSlider, QLineEdit,
    QStackedWidget,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QFontDatabase

from neopathgen.palette import *
from neopathgen.viewport import *

from neopathgen.utils.helpers import *
from neopathgen.utils.speed_profile import *
from neopathgen.utils.spline import *
from neopathgen.utils.stereo import *

class Stage4Panel(QWidget):
    """
    Left panel for Stage 4 (Stereo offset).

    Signals
    -------
    generate_requested()
    export_requested()
    offset_changed(float)
    show_left_changed(bool)
    show_right_changed(bool)
    """
    generate_requested = pyqtSignal()
    export_requested   = pyqtSignal()
    offset_changed     = pyqtSignal(float)
    show_left_changed  = pyqtSignal(bool)
    show_right_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(Stage4Panel, self).__init__(parent)
        self.setFixedWidth(265)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 14, 12, 10)
        bl.setSpacing(4)
        scroll.setWidget(body)
        root.addWidget(scroll)

        # Title
        title = QLabel("NEOPATHGEN")
        title.setObjectName("AppTitle")
        bl.addWidget(title)
        sub = QLabel("stereo offset")
        sub.setStyleSheet("color: %s; font-size: 9px; letter-spacing: 2px;"
                          % C["text_muted"])
        bl.addWidget(sub)
        bl.addSpacing(10)

        # ── Info ─────────────────────────────────────────────────────────────
        info = QLabel(
            "Generates two paths offset laterally by ±½ of the distance "
            "below.\n\nLateral = normalize(direction × north)\n"
            "Direction and north are identical for both eyes.")
        info.setStyleSheet("color: %s; font-size: 10px;" % C["text_dim"])
        info.setWordWrap(True)
        bl.addWidget(info)
        bl.addSpacing(8)

        # ── Offset distance ───────────────────────────────────────────────────
        bl.addWidget(sec_label("INTER-OCULAR DISTANCE"))
        bl.addWidget(hdivider())

        offset_row = QWidget()
        orl = QHBoxLayout(offset_row)
        orl.setContentsMargins(0, 0, 0, 0); orl.setSpacing(6)
        orl.addWidget(QLabel("Offset"))
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(0.0, 9999.0)
        self.spin_offset.setValue(0.1)
        self.spin_offset.setSingleStep(0.01)
        self.spin_offset.setDecimals(4)
        self.spin_offset.setFixedWidth(100)
        orl.addStretch()
        orl.addWidget(self.spin_offset)
        bl.addWidget(offset_row)
        bl.addSpacing(8)

        # ── Source ────────────────────────────────────────────────────────────
        bl.addWidget(sec_label("SOURCE DATA"))
        bl.addWidget(hdivider())

        self.lbl_source = QLabel("Will use Stage 2 uniform splines.")
        self.lbl_source.setStyleSheet(
            "color: %s; font-size: 10px;" % C["text_dim"])
        self.lbl_source.setWordWrap(True)
        bl.addWidget(self.lbl_source)
        bl.addSpacing(8)

        # ── Generate ──────────────────────────────────────────────────────────
        bl.addWidget(sec_label("GENERATE"))
        bl.addWidget(hdivider())

        self.btn_generate = btn("Generate Offset Paths", "primary", "⇔")
        self.btn_generate.setFixedHeight(32)
        bl.addWidget(self.btn_generate)

        self.lbl_status = QLabel("No offset generated.")
        self.lbl_status.setStyleSheet(
            "color: %s; font-size: 10px;" % C["text_muted"])
        self.lbl_status.setWordWrap(True)
        bl.addWidget(self.lbl_status)
        bl.addSpacing(8)

        # ── Visibility ────────────────────────────────────────────────────────
        bl.addWidget(sec_label("VISIBILITY"))
        bl.addWidget(hdivider())

        self.chk_show_left  = QCheckBox("Show left path")
        self.chk_show_right = QCheckBox("Show right path")
        self.chk_show_left.setChecked(True)
        self.chk_show_right.setChecked(True)
        self.chk_show_left.setStyleSheet(
            "color: %s;" % C["col_direction"])
        self.chk_show_right.setStyleSheet(
            "color: %s;" % C["col_north"])
        bl.addWidget(self.chk_show_left)
        bl.addWidget(self.chk_show_right)
        bl.addSpacing(8)

        # ── Export ────────────────────────────────────────────────────────────
        bl.addWidget(sec_label("EXPORT"))
        bl.addWidget(hdivider())

        self.btn_export = btn("Export Left + Right (.txt)", "success", "↗")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setEnabled(False)
        bl.addWidget(self.btn_export)

        self.lbl_export = QLabel("Generate offset paths first.")
        self.lbl_export.setStyleSheet(
            "color: %s; font-size: 10px;" % C["text_muted"])
        self.lbl_export.setWordWrap(True)
        bl.addWidget(self.lbl_export)
        bl.addStretch()

        # Wiring
        self.btn_generate.clicked.connect(self.generate_requested)
        self.btn_export.clicked.connect(self.export_requested)
        self.spin_offset.valueChanged.connect(self.offset_changed)
        self.chk_show_left.toggled.connect(self.show_left_changed)
        self.chk_show_right.toggled.connect(self.show_right_changed)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_source_label(self, has_retimed):
        if has_retimed:
            self.lbl_source.setText("✓  Using Stage 3 re-timed arrays.")
            self.lbl_source.setStyleSheet(
                "color: %s; font-size: 10px;" % C["success"])
        else:
            self.lbl_source.setText(
                "Using Stage 2 uniform splines\n"
                "(run Stage 3 first to use re-timed data).")
            self.lbl_source.setStyleSheet(
                "color: %s; font-size: 10px;" % C["text_dim"])

    def set_generate_status(self, ok, message):
        color = C["success"] if ok else C["danger"]
        self.lbl_status.setStyleSheet("color: %s; font-size: 10px;" % color)
        self.lbl_status.setText(message)
        self.btn_export.setEnabled(ok)
        if ok:
            self.lbl_export.setText("Ready — choose a base filename.")
            self.lbl_export.setStyleSheet(
                "color: %s; font-size: 10px;" % C["text_dim"])
        else:
            self.lbl_export.setText("Generate offset paths first.")
            self.lbl_export.setStyleSheet(
                "color: %s; font-size: 10px;" % C["text_muted"])

    def set_export_status(self, message):
        self.lbl_export.setText(message)
        self.lbl_export.setStyleSheet(
            "color: %s; font-size: 10px;" % C["success"])

    def load_from_project(self, proj):
        self.spin_offset.blockSignals(True)
        self.spin_offset.setValue(float(proj.get("stereo_offset", 0.1)))
        self.spin_offset.blockSignals(False)


def _placeholder_panel(title, subtitle=""):
    w = QWidget()
    l = QVBoxLayout(w)
    l.setAlignment(Qt.AlignCenter)
    t = QLabel(title)
    t.setStyleSheet("color: %s; font-size: 12px; letter-spacing: 3px;" % C["text_muted"])
    t.setAlignment(Qt.AlignCenter)
    l.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet("color: %s; font-size: 10px;" % C["text_muted"])
        s.setAlignment(Qt.AlignCenter)
        l.addWidget(s)
    return w
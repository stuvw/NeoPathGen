# ══════════════════════════════════════════════════════════════════════════════
# Speed curve canvas (pure Qt painter — no Vispy)
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QToolBar, QStatusBar,
    QSizePolicy, QGroupBox, QTabWidget, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QFileDialog,
    QMessageBox, QAbstractItemView, QScrollArea, QSlider, QLineEdit,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QFont, QColor, QFontDatabase, QPainter, QPen, QBrush, QPainterPath, QPolygonF


from neopathgen.palette import *

from neopathgen.utils.helpers import *
from neopathgen.utils.speed_profile import *
from neopathgen.utils.spline import *

class SpeedCurveWidget(QWidget):
    """
    Read-only 2-D plot of the resolved speed multiplier m(u).

    Call update_curve(profile_list) to refresh.
    """
    def __init__(self, parent=None):
        super(SpeedCurveWidget, self).__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._u   = np.linspace(0.0, 1.0, 400)
        self._m   = np.ones(400)
        self._segs = []   # list of (start, end, speed) for segment shading
        self._m_max = 2.0

    def update_curve(self, profile_list):
        self._segs = sorted(
            [(float(s["start"]), float(s["end"]), float(s["speed"]))
             for s in profile_list],
            key=lambda x: x[0]
        )
        self._u, self._m = eval_speed_curve(profile_list)
        self._m_max = max(2.0, float(self._m.max()) * 1.15)
        self.update()

    def paintEvent(self, event):
        w, h  = self.width(), self.height()
        pad_l, pad_r = 42, 16
        pad_t, pad_b = 14, 30
        pw = w - pad_l - pad_r   # plot area width
        ph = h - pad_t - pad_b   # plot area height

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background
        p.fillRect(0, 0, w, h, QBrush(QColor(C["bg"])))
        p.fillRect(pad_l, pad_t, pw, ph, QBrush(QColor(C["surface"])))

        def ux(u):   return pad_l + u * pw
        def my(m):   return pad_t + ph - (m / self._m_max) * ph

        # Grid lines at m = 0.5, 1.0, 1.5, ...
        pen_grid = QPen(QColor(C["panel_border"]))
        pen_grid.setWidth(1)
        p.setPen(pen_grid)
        tick = 0.5
        mv = tick
        while mv <= self._m_max + 1e-6:
            y = int(my(mv))
            if pad_t <= y <= pad_t + ph:
                p.drawLine(pad_l, y, pad_l + pw, y)
                p.setPen(QPen(QColor(C["text_muted"])))
                p.drawText(2, y + 4, "%g" % mv)
                p.setPen(pen_grid)
            mv += tick

        # u=0 and u=1 verticals
        p.drawLine(pad_l, pad_t, pad_l, pad_t + ph)

        # Segment shading
        for (a, b, v) in self._segs:
            x0 = int(ux(a)); x1 = int(ux(b))
            shade = QColor(C["accent_dim"])
            shade.setAlpha(40)
            p.fillRect(x0, pad_t, x1 - x0, ph, QBrush(shade))

        # m=1 reference line
        pen_ref = QPen(QColor(C["text_muted"]))
        pen_ref.setStyle(Qt.DashLine)
        pen_ref.setWidth(1)
        p.setPen(pen_ref)
        y1 = int(my(1.0))
        p.drawLine(pad_l, y1, pad_l + pw, y1)

        # Resolved m(u) curve — filled area + stroke
        if len(self._u) > 1:
            path = QPainterPath()
            path.moveTo(QPointF(ux(self._u[0]), my(self._m[0])))
            for i in range(1, len(self._u)):
                path.lineTo(QPointF(ux(self._u[i]), my(self._m[i])))

            # Fill under the curve
            fill_path = QPainterPath(path)
            fill_path.lineTo(QPointF(ux(self._u[-1]), pad_t + ph))
            fill_path.lineTo(QPointF(ux(self._u[0]),  pad_t + ph))
            fill_path.closeSubpath()
            fill_col = QColor(C["accent"])
            fill_col.setAlpha(30)
            p.fillPath(fill_path, QBrush(fill_col))

            # Stroke
            pen_curve = QPen(QColor(C["accent"]))
            pen_curve.setWidth(2)
            p.setPen(pen_curve)
            p.drawPath(path)

        # Axis labels
        p.setPen(QPen(QColor(C["text_dim"])))
        p.drawText(pad_l, pad_t + ph + 18, "0")
        p.drawText(pad_l + pw - 6, pad_t + ph + 18, "1")
        p.drawText(pad_l + pw // 2 - 8, pad_t + ph + 18, "u")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3 panel
# ══════════════════════════════════════════════════════════════════════════════

class Stage3Panel(QWidget):
    """
    Left panel for Stage 3 (Speed profile).

    Signals
    -------
    apply_requested()
    export_requested()
    profile_changed(list)   — emitted whenever the table is edited
    """
    apply_requested  = pyqtSignal()
    export_requested = pyqtSignal()
    profile_changed  = pyqtSignal(list)
    show_retimed_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(Stage3Panel, self).__init__(parent)
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
        sub = QLabel("speed profile")
        sub.setStyleSheet("color: %s; font-size: 9px; letter-spacing: 2px;" % C["text_muted"])
        bl.addWidget(sub)
        bl.addSpacing(10)

        # ── Info ──────────────────────────────────────────────────────────────
        info = QLabel(
            "Define speed multipliers over the path parameter u ∈ [0,1].\n"
            "Gaps between segments are smoothly bridged.\n"
            "Speed = 1.0 is normal, 2.0 = twice as fast, 0.5 = half speed.")
        info.setStyleSheet("color: %s; font-size: 10px;" % C["text_dim"])
        info.setWordWrap(True)
        bl.addWidget(info)
        bl.addSpacing(8)

        # ── Segment table ──────────────────────────────────────────────────────
        bl.addWidget(sec_label("SEGMENTS"))
        bl.addWidget(hdivider())

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Speed"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background: %s; color: %s; "
            "font-size: 9px; letter-spacing: 1px; border: none; "
            "border-bottom: 1px solid %s; padding: 4px; }"
            % (C["surface2"], C["text_muted"], C["panel_border"]))
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(160)
        self.table.setStyleSheet(
            "QTableWidget { gridline-color: %s; }" % C["panel_border"])
        bl.addWidget(self.table)

        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 2, 0, 0); brl.setSpacing(4)
        self.btn_add_seg = btn("Add",    "primary", "+")
        self.btn_del_seg = btn("Delete", "danger",  "×")
        self.btn_add_seg.setFixedHeight(26)
        self.btn_del_seg.setFixedHeight(26)
        brl.addWidget(self.btn_add_seg); brl.addWidget(self.btn_del_seg)
        bl.addWidget(btn_row)
        bl.addSpacing(8)

        # ── Apply ─────────────────────────────────────────────────────────────
        bl.addWidget(sec_label("APPLY TO"))
        bl.addWidget(hdivider())

        self.chk_retime_path  = QCheckBox("Re-time path")
        self.chk_retime_dir   = QCheckBox("Re-time direction")
        self.chk_retime_north = QCheckBox("Re-time north")
        self.chk_retime_path.setChecked(True)
        self.chk_retime_dir.setChecked(True)
        self.chk_retime_north.setChecked(True)
        # Path is mandatory — disabling would make no sense
        self.chk_retime_path.setEnabled(False)
        self.chk_retime_path.setStyleSheet(
            "color: %s;" % C["col_path"])
        self.chk_retime_dir.setStyleSheet(
            "color: %s;" % C["col_direction"])
        self.chk_retime_north.setStyleSheet(
            "color: %s;" % C["col_north"])
        for chk in (self.chk_retime_path, self.chk_retime_dir,
                    self.chk_retime_north):
            bl.addWidget(chk)
        bl.addSpacing(6)

        self.btn_apply = btn("Apply Speed Profile", "primary", "▶")
        self.btn_apply.setFixedHeight(32)
        bl.addWidget(self.btn_apply)

        self.lbl_status = QLabel("No profile applied yet.")
        self.lbl_status.setStyleSheet("color: %s; font-size: 10px;" % C["text_muted"])
        self.lbl_status.setWordWrap(True)
        bl.addWidget(self.lbl_status)
        bl.addSpacing(8)

        # ── Export ────────────────────────────────────────────────────────────
        bl.addWidget(sec_label("EXPORT"))
        bl.addWidget(hdivider())

        self.btn_export = btn("Export Re-timed Path", "success", "↗")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setEnabled(False)
        bl.addWidget(self.btn_export)

        self.lbl_export = QLabel("Apply profile first.")
        self.lbl_export.setStyleSheet("color: %s; font-size: 10px;" % C["text_muted"])
        self.lbl_export.setWordWrap(True)
        bl.addWidget(self.lbl_export)
        bl.addSpacing(8)

        # ── Visibility ────────────────────────────────────────────────────────
        bl.addWidget(sec_label("VISIBILITY"))
        bl.addWidget(hdivider())

        self.chk_show_retimed = QCheckBox("Show re-timed dot cloud")
        self.chk_show_retimed.setChecked(True)
        bl.addWidget(self.chk_show_retimed)
        bl.addStretch()

        # Wiring
        self.btn_add_seg.clicked.connect(self._add_segment)
        self.btn_del_seg.clicked.connect(self._delete_segment)
        self.btn_apply.clicked.connect(self.apply_requested)
        self.btn_export.clicked.connect(self.export_requested)
        self.table.itemChanged.connect(self._on_table_changed)
        self.chk_show_retimed.toggled.connect(self.show_retimed_changed)

    # ── Table helpers ─────────────────────────────────────────────────────────

    def _add_segment(self):
        """Append a new row with sensible defaults."""
        row = self.table.rowCount()
        # Default: pick up where last segment ended, or start at 0
        if row > 0:
            prev_end = self._cell_value(row - 1, 1)
            start = min(prev_end, 0.99)
        else:
            start = 0.0
        end   = min(start + 0.25, 1.0)
        speed = 1.0
        self.table.blockSignals(True)
        self.table.insertRow(row)
        for col, val in enumerate([start, end, speed]):
            item = QTableWidgetItem("%.3f" % val)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self._emit_profile()

    def _delete_segment(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._emit_profile()

    def _cell_value(self, row, col):
        item = self.table.item(row, col)
        try:
            return float(item.text())
        except (ValueError, AttributeError):
            return 0.0

    def _on_table_changed(self, item):
        # Clamp values to valid ranges
        row, col = item.row(), item.column()
        try:
            v = float(item.text())
        except ValueError:
            return
        self.table.blockSignals(True)
        if col in (0, 1):   # start / end: clamp to [0, 1]
            v = max(0.0, min(1.0, v))
        elif col == 2:       # speed: clamp to (0, ∞)
            v = max(0.001, v)
        item.setText("%.3f" % v)
        self.table.blockSignals(False)
        self._emit_profile()

    def _emit_profile(self):
        prof = []
        for row in range(self.table.rowCount()):
            prof.append({
                "start": self._cell_value(row, 0),
                "end":   self._cell_value(row, 1),
                "speed": self._cell_value(row, 2),
            })
        self.profile_changed.emit(prof)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_profile(self):
        prof = []
        for row in range(self.table.rowCount()):
            prof.append({
                "start": self._cell_value(row, 0),
                "end":   self._cell_value(row, 1),
                "speed": self._cell_value(row, 2),
            })
        return prof

    def get_retime_targets(self):
        """Return dict of which arrays should be re-timed."""
        return {
            "path":      True,   # always
            "direction": self.chk_retime_dir.isChecked(),
            "north":     self.chk_retime_north.isChecked(),
        }

    def set_apply_status(self, ok, message):
        color = C["success"] if ok else C["danger"]
        self.lbl_status.setStyleSheet("color: %s; font-size: 10px;" % color)
        self.lbl_status.setText(message)
        self.btn_export.setEnabled(ok)
        if ok:
            self.lbl_export.setText("Ready to export.")
            self.lbl_export.setStyleSheet("color: %s; font-size: 10px;" % C["text_dim"])
        else:
            self.lbl_export.setText("Apply profile first.")
            self.lbl_export.setStyleSheet("color: %s; font-size: 10px;" % C["text_muted"])

    def set_export_status(self, message):
        self.lbl_export.setText(message)
        self.lbl_export.setStyleSheet("color: %s; font-size: 10px;" % C["success"])

    def load_from_project(self, proj):
        """Populate the table from a loaded project dict."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for seg in proj.get("speed_profile", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(["start", "end", "speed"]):
                item = QTableWidgetItem("%.3f" % float(seg.get(key, 0.0)))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
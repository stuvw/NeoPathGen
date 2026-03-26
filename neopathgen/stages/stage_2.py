# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 panel
# ══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import (
    QScrollArea, QSpinBox, QCheckBox, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal


from neopathgen.palette import C

from neopathgen.utils.helpers import hdivider, sec_label, btn

class Stage2Panel(QWidget):
    """
    Left panel for Stage 2 (Spline generation & export).

    Signals
    -------
    generate_requested()
    export_requested()
    spline_param_changed(layer, key, value)
        layer in ("path","direction","north"), key in ("smoothness","closed")
    resolution_changed(int)
    show_dir_vectors_changed(bool)
    show_north_vectors_changed(bool)
    """
    generate_requested       = pyqtSignal()
    export_requested         = pyqtSignal()
    spline_param_changed     = pyqtSignal(str, str, object)
    resolution_changed       = pyqtSignal(int)
    show_dir_vectors_changed   = pyqtSignal(bool)
    show_north_vectors_changed = pyqtSignal(bool)
    show_spline_changed        = pyqtSignal(str, bool)   # (layer, visible)

    def __init__(self, parent=None):
        super(Stage2Panel, self).__init__(parent)
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
        sub = QLabel("spline generation")
        sub.setStyleSheet(f"color: {C["text_muted"]}; font-size: 9px; letter-spacing: 2px;")
        bl.addWidget(sub)
        bl.addSpacing(10)

        # ── Shared resolution ─────────────────────────────────────────────────
        bl.addWidget(sec_label("RESOLUTION  (all splines)"))
        bl.addWidget(hdivider())

        res_row = QWidget()
        rl = QHBoxLayout(res_row)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(6)
        rl.addWidget(QLabel("Samples"))
        self.spin_resolution = QSpinBox()
        self.spin_resolution.setRange(10, 100000)
        self.spin_resolution.setValue(500)
        self.spin_resolution.setSingleStep(100)
        self.spin_resolution.setFixedWidth(90)
        rl.addStretch()
        rl.addWidget(self.spin_resolution)
        bl.addWidget(res_row)
        bl.addSpacing(8)

        # ── Per-layer parameters ──────────────────────────────────────────────
        self._layer_widgets = {}   # layer → {"smooth": spin, "closed": chk}

        for layer, col in [("path",      C["col_path"]),
                            ("direction", C["col_direction"]),
                            ("north",     C["col_north"])]:
            lbl = QLabel(f"■  {layer.upper()}")
            lbl.setStyleSheet(f"color: {col}; font-size: 9px; font-weight: bold;"
                              " letter-spacing: 2px; padding-top: 6px;")
            bl.addWidget(lbl)
            bl.addWidget(hdivider())

            sm_row = QWidget()
            sl = QHBoxLayout(sm_row)
            sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(6)
            sl.addWidget(QLabel("Smoothness"))
            spin_sm = QDoubleSpinBox()
            spin_sm.setRange(0.0, 1000.0)
            spin_sm.setValue(0.0)
            spin_sm.setSingleStep(0.1)
            spin_sm.setDecimals(3)
            spin_sm.setFixedWidth(90)
            sl.addStretch()
            sl.addWidget(spin_sm)
            bl.addWidget(sm_row)

            chk_cl = QCheckBox("Closed loop")
            bl.addWidget(chk_cl)
            bl.addSpacing(4)

            self._layer_widgets[layer] = {"smooth": spin_sm, "closed": chk_cl}

            # closures to capture layer
            def _make_sm_handler(lyr, sp):
                def h(v): self.spline_param_changed.emit(lyr, "smoothness", v)
                return h
            def _make_cl_handler(lyr, ck):
                def h(v): self.spline_param_changed.emit(lyr, "closed", bool(v))
                return h
            spin_sm.valueChanged.connect(_make_sm_handler(layer, spin_sm))
            chk_cl.toggled.connect(_make_cl_handler(layer, chk_cl))

        bl.addSpacing(4)

        # ── Vector field display ──────────────────────────────────────────────
        bl.addWidget(sec_label("VISIBILITY"))
        bl.addWidget(hdivider())

        self.chk_show_dir   = QCheckBox("Show direction vectors")
        self.chk_show_north = QCheckBox("Show north vectors")
        self.chk_show_dir.setChecked(True)
        self.chk_show_north.setChecked(True)
        bl.addWidget(self.chk_show_dir)
        bl.addWidget(self.chk_show_north)

        self.chk_show_spline = {}
        for layer, col, label in [
            ("path",      C["col_path"],      "Show path spline"),
            ("direction", C["col_direction"], "Show direction spline"),
            ("north",     C["col_north"],     "Show north spline"),
        ]:
            chk = QCheckBox(label)
            chk.setChecked(True)
            chk.setStyleSheet(f"color: {col};")
            bl.addWidget(chk)
            self.chk_show_spline[layer] = chk
        bl.addSpacing(8)

        # ── Active layers info ────────────────────────────────────────────────
        bl.addWidget(sec_label("LAYER SUMMARY"))
        bl.addWidget(hdivider())

        self.lbl_path_info  = QLabel("PATH      – 0 pts")
        self.lbl_dir_info   = QLabel("DIRECTION – mode: tangent")
        self.lbl_north_info = QLabel("NORTH     – mode: fixed Z")
        for lbl in (self.lbl_path_info, self.lbl_dir_info, self.lbl_north_info):
            lbl.setStyleSheet(f"color: {C["text_dim"]}; font-size: 10px;")
            lbl.setWordWrap(True)
            bl.addWidget(lbl)
        bl.addSpacing(8)

        # ── Generate ──────────────────────────────────────────────────────────
        bl.addWidget(sec_label("GENERATE"))
        bl.addWidget(hdivider())

        self.btn_generate = btn("Generate Splines", "primary", "∿")
        self.btn_generate.setFixedHeight(32)
        bl.addWidget(self.btn_generate)

        self.lbl_status = QLabel("No spline generated")
        self.lbl_status.setStyleSheet(f"color: {C["text_muted"]}; font-size: 10px;")
        self.lbl_status.setWordWrap(True)
        bl.addWidget(self.lbl_status)
        bl.addSpacing(8)

        # ── Export ────────────────────────────────────────────────────────────
        bl.addWidget(sec_label("EXPORT"))
        bl.addWidget(hdivider())

        self.btn_export = btn("Export Path (.txt)", "success", "↗")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setEnabled(False)
        bl.addWidget(self.btn_export)

        self.lbl_export = QLabel("Generate a spline first.")
        self.lbl_export.setStyleSheet(f"color: {C["text_muted"]}; font-size: 10px;")
        self.lbl_export.setWordWrap(True)
        bl.addWidget(self.lbl_export)
        bl.addStretch()

        # Wiring
        self.btn_generate.clicked.connect(self.generate_requested)
        self.btn_export.clicked.connect(self.export_requested)
        self.spin_resolution.valueChanged.connect(self.resolution_changed)
        self.chk_show_dir.toggled.connect(self.show_dir_vectors_changed)
        self.chk_show_north.toggled.connect(self.show_north_vectors_changed)
        for layer, chk in self.chk_show_spline.items():
            def _make_spline_handler(lyr):
                def h(v): self.show_spline_changed.emit(lyr, v)
                return h
            chk.toggled.connect(_make_spline_handler(layer))

    # ── Public API ────────────────────────────────────────────────────────────

    def set_generate_status(self, ok, message):
        color = C["success"] if ok else C["danger"]
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.lbl_status.setText(message)
        self.btn_export.setEnabled(ok)
        if ok:
            self.lbl_export.setText("Ready to export.")
            self.lbl_export.setStyleSheet(f"color: {C["text_dim"]}; font-size: 10px;")
        else:
            self.lbl_export.setText("Generate a spline first.")
            self.lbl_export.setStyleSheet(f"color: {C["text_muted"]}; font-size: 10px;")

    def set_export_status(self, message):
        self.lbl_export.setText(message)
        self.lbl_export.setStyleSheet(f"color: {C["success"]}; font-size: 10px;")

    def refresh_layer_info(self, project):
        n_path = len(project["path"]["points"])
        d_mode = project["direction"]["mode"]
        n_dir  = len(project["direction"]["points"])
        n_mode = project["north"]["mode"]
        n_nor  = len(project["north"]["points"])

        self.lbl_path_info.setText(f"PATH      – {n_path} pts")
        dir_detail = (f" ({n_dir} ctrl pts)") if d_mode == "spline" else ""
        self.lbl_dir_info.setText(f"DIRECTION – {d_mode}{dir_detail}")
        nor_detail = (f" ({n_nor} ctrl pts)") if n_mode == "spline" else ""
        self.lbl_north_info.setText(f"NORTH     – {n_mode}{nor_detail}")

    def load_from_project(self, proj):
        sp = proj["spline"]
        self.spin_resolution.blockSignals(True)
        self.spin_resolution.setValue(sp["resolution"])
        self.spin_resolution.blockSignals(False)

        for layer in ("path", "direction", "north"):
            src = proj["path"]["points"] if layer == "path" else proj[layer]
            w   = self._layer_widgets[layer]
            w["smooth"].blockSignals(True)
            w["closed"].blockSignals(True)
            if layer == "path":
                w["smooth"].setValue(proj["spline"]["smoothness"])
                w["closed"].setChecked(proj["spline"]["closed"])
            else:
                w["smooth"].setValue(src.get("smoothness", 0.0))
                w["closed"].setChecked(src.get("closed", False))
            w["smooth"].blockSignals(False)
            w["closed"].blockSignals(False)
# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 side panel
# ══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QComboBox, QCheckBox, 
    QAbstractItemView, QScrollArea, QSlider,
    QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from neopathgen.palette import C

from neopathgen.utils.helpers import sec_label, hdivider, btn, xyz_row

class Stage1Panel(QWidget):
    layer_changed             = pyqtSignal(str)
    mode_changed              = pyqtSignal(str, str)
    add_point_requested       = pyqtSignal()
    delete_point_requested    = pyqtSignal()
    clear_all_requested       = pyqtSignal()
    point_selected            = pyqtSignal(int)
    point_x_changed           = pyqtSignal(int, float)
    point_y_changed           = pyqtSignal(int, float)
    point_z_changed           = pyqtSignal(int, float)
    fixed_vector_changed      = pyqtSignal(str, float, float, float)
    fixed_point_changed       = pyqtSignal(str, float, float, float)
    mesh_load_requested       = pyqtSignal()
    mesh_toggle               = pyqtSignal(bool)
    pointcloud_load_requested = pyqtSignal()
    pointcloud_toggle         = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(Stage1Panel, self).__init__(parent)
        self.setFixedWidth(265)
        self._current_layer = "path"
        self._coord_syncing = False
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
        sub = QLabel("camera path generator")
        sub.setStyleSheet("color: %s; font-size: 9px; letter-spacing: 2px;" % C["text_muted"])
        bl.addWidget(sub)
        bl.addSpacing(10)

        # ── Active layer
        bl.addWidget(sec_label("ACTIVE LAYER"))
        bl.addWidget(hdivider())

        self.layer_combo = QComboBox()
        self.layer_combo.addItems(["PATH  (position)", "DIRECTION  (camera dir)", "NORTH  (up vector)"])
        bl.addWidget(self.layer_combo)
        bl.addSpacing(4)

        swatch_row = QWidget()
        shl = QHBoxLayout(swatch_row)
        shl.setContentsMargins(0, 0, 0, 0); shl.setSpacing(8)
        for layer, col in [("PATH", C["col_path"]), ("DIR", C["col_direction"]), ("NORTH", C["col_north"])]:
            sw = QLabel("■ %s" % layer)
            sw.setStyleSheet("color: %s; font-size: 9px; letter-spacing: 1px;" % col)
            shl.addWidget(sw)
        shl.addStretch()
        bl.addWidget(swatch_row)
        bl.addSpacing(8)

        # ── Direction mode
        bl.addWidget(sec_label("DIRECTION MODE"))
        bl.addWidget(hdivider())

        self.dir_mode_combo = QComboBox()
        self.dir_mode_combo.addItems(["Auto-tangent", "Spline", "Look-at point", "Fixed vector"])
        bl.addWidget(self.dir_mode_combo)

        self._dir_stack = QStackedWidget()
        # 0: tangent — no extra
        self._dir_stack.addWidget(QWidget())
        # 1: spline — no extra
        self._dir_stack.addWidget(QWidget())
        # 2: look-at point
        w2 = QWidget(); v2 = QVBoxLayout(w2); v2.setContentsMargins(0, 4, 0, 0)
        self._dir_lookat_row, self._dir_lx, self._dir_ly, self._dir_lz = xyz_row("→")
        v2.addWidget(self._dir_lookat_row)
        self._dir_stack.addWidget(w2)
        # 3: fixed vector
        w3 = QWidget(); v3 = QVBoxLayout(w3); v3.setContentsMargins(0, 4, 0, 0)
        self._dir_vec_row, self._dir_vx, self._dir_vy, self._dir_vz = xyz_row("→")
        v3.addWidget(self._dir_vec_row)
        self._dir_stack.addWidget(w3)
        bl.addWidget(self._dir_stack)
        bl.addSpacing(8)

        # ── North mode
        bl.addWidget(sec_label("NORTH MODE"))
        bl.addWidget(hdivider())

        self.north_mode_combo = QComboBox()
        self.north_mode_combo.addItems(["Fixed vector (Z-up)", "Spline", "Fixed point"])
        bl.addWidget(self.north_mode_combo)

        self._north_stack = QStackedWidget()
        # 0: fixed vector
        nw0 = QWidget(); nv0 = QVBoxLayout(nw0); nv0.setContentsMargins(0, 4, 0, 0)
        self._north_vec_row, self._north_vx, self._north_vy, self._north_vz = xyz_row("↑")
        self._north_vz.setValue(1.0)
        nv0.addWidget(self._north_vec_row)
        self._north_stack.addWidget(nw0)
        # 1: spline
        self._north_stack.addWidget(QWidget())
        # 2: fixed point
        nw2 = QWidget(); nv2 = QVBoxLayout(nw2); nv2.setContentsMargins(0, 4, 0, 0)
        self._north_pt_row, self._north_px, self._north_py, self._north_pz = xyz_row("↑")
        nv2.addWidget(self._north_pt_row)
        self._north_stack.addWidget(nw2)
        bl.addWidget(self._north_stack)
        bl.addSpacing(8)

        # ── Control points
        bl.addWidget(sec_label("CONTROL POINTS"))
        bl.addWidget(hdivider())

        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0); brl.setSpacing(4)
        self.btn_add    = btn("Add",    "primary", "+")
        self.btn_delete = btn("Delete", "danger",  "×")
        self.btn_add.setFixedHeight(28); self.btn_delete.setFixedHeight(28)
        brl.addWidget(self.btn_add); brl.addWidget(self.btn_delete)
        bl.addWidget(btn_row)

        self.btn_clear = btn("Clear All", "danger", "⊘")
        self.btn_clear.setFixedHeight(26)
        bl.addWidget(self.btn_clear)
        bl.addSpacing(4)

        self.point_list = QListWidget()
        self.point_list.setFixedHeight(150)
        self.point_list.setSelectionMode(QAbstractItemView.SingleSelection)
        bl.addWidget(self.point_list)

        # ── X / Y / Z controls for selected point ────────────────────────────
        bl.addWidget(sec_label("SELECTED POINT"))

        def coord_row(axis_label):
            """Return (container widget, QDoubleSpinBox, QSlider)."""
            w  = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 2, 0, 2)
            hl.setSpacing(5)
            lbl = QLabel(axis_label)
            lbl.setFixedWidth(12)
            lbl.setStyleSheet("color: %s; font-size: 10px; font-weight: bold;" % C["text_muted"])
            spin = QDoubleSpinBox()
            spin.setRange(-9999, 9999)
            spin.setSingleStep(0.1)
            spin.setDecimals(3)
            spin.setFixedWidth(82)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-1000, 1000)   # ÷ 10 → −100 … -100
            hl.addWidget(lbl)
            hl.addWidget(spin)
            hl.addWidget(slider)
            return w, spin, slider

        coord_container = QWidget()
        ccl = QVBoxLayout(coord_container)
        ccl.setContentsMargins(0, 4, 0, 0)
        ccl.setSpacing(0)

        xw, self.x_spin, self.x_slider = coord_row("X")
        yw, self.y_spin, self.y_slider = coord_row("Y")
        zw, self.z_spin, self.z_slider = coord_row("Z")
        ccl.addWidget(xw); ccl.addWidget(yw); ccl.addWidget(zw)
        bl.addWidget(coord_container)
        bl.addSpacing(8)

        # ── Reference mesh
        bl.addWidget(sec_label("REFERENCE MESH"))
        bl.addWidget(hdivider())

        mesh_row = QWidget()
        ml = QHBoxLayout(mesh_row)
        ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(4)
        self.btn_load_mesh = btn("Load OBJ/PLY", icon="▲")
        self.btn_load_mesh.setFixedHeight(28)
        self.chk_mesh = QCheckBox("Show")
        self.chk_mesh.setChecked(True)
        ml.addWidget(self.btn_load_mesh, 1); ml.addWidget(self.chk_mesh)
        bl.addWidget(mesh_row)
        self.lbl_mesh = QLabel("No mesh loaded")
        self.lbl_mesh.setStyleSheet("color: %s; font-size: 9px;" % C["text_muted"])
        bl.addWidget(self.lbl_mesh)
        bl.addStretch()

        # ── Reference point cloud

        bl.addWidget(sec_label("POINT CLOUD"))
        bl.addWidget(hdivider())

        pc_row = QWidget()
        pl = QHBoxLayout(pc_row)
        pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(4)
        self.btn_load_pointcloud = btn("Load .bin", icon="▲")
        self.btn_load_pointcloud.setFixedHeight(28)
        self.chk_pointcloud = QCheckBox("Show")
        self.chk_pointcloud.setChecked(True)
        pl.addWidget(self.btn_load_pointcloud, 1)
        pl.addWidget(self.chk_pointcloud)
        bl.addWidget(pc_row)
        self.lbl_pointcloud = QLabel("No point cloud loaded")
        self.lbl_pointcloud.setStyleSheet(
            "color: %s; font-size: 9px;" % C["text_muted"])
        bl.addWidget(self.lbl_pointcloud)
        

        # Wiring
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.dir_mode_combo.currentIndexChanged.connect(self._on_dir_mode)
        self.north_mode_combo.currentIndexChanged.connect(self._on_north_mode)
        self.btn_add.clicked.connect(self.add_point_requested)
        self.btn_delete.clicked.connect(self.delete_point_requested)
        self.btn_clear.clicked.connect(self.clear_all_requested)
        self.point_list.currentRowChanged.connect(self._on_row_changed)
        # X / Y / Z spin↔slider sync + signal emission
        self._connect_coord_handlers()
        self.btn_load_mesh.clicked.connect(self.mesh_load_requested)
        self.chk_mesh.toggled.connect(self.mesh_toggle)
        self.btn_load_pointcloud.clicked.connect(self.pointcloud_load_requested)
        self.chk_pointcloud.toggled.connect(self.pointcloud_toggle)

        for sb in (self._dir_lx, self._dir_ly, self._dir_lz):
            sb.valueChanged.connect(self._emit_dir_lookat)
        for sb in (self._dir_vx, self._dir_vy, self._dir_vz):
            sb.valueChanged.connect(self._emit_dir_vec)
        for sb in (self._north_vx, self._north_vy, self._north_vz):
            sb.valueChanged.connect(self._emit_north_vec)
        for sb in (self._north_px, self._north_py, self._north_pz):
            sb.valueChanged.connect(self._emit_north_pt)

    def _on_layer_changed(self, idx):
        self._current_layer = ["path", "direction", "north"][idx]
        self.layer_changed.emit(self._current_layer)

    def _on_dir_mode(self, idx):
        self._dir_stack.setCurrentIndex(idx)
        self.mode_changed.emit("direction",
            ["tangent", "spline", "look_at", "fixed_vector"][idx])

    def _on_north_mode(self, idx):
        self._north_stack.setCurrentIndex(idx)
        self.mode_changed.emit("north",
            ["fixed_vector", "spline", "fixed_point"][idx])

    def _on_row_changed(self, row):
        self.point_selected.emit(row)

    # ── Generic coord handler factory ─────────────────────────────────────────

    def _make_coord_handlers(self, spin, slider, signal):
        """Return (on_spin, on_slider) closures for one axis."""
        def on_spin(val):
            if self._coord_syncing: return
            row = self.point_list.currentRow()
            if row < 0: return
            self._coord_syncing = True
            slider.setValue(int(val * 10))
            self._coord_syncing = False
            signal.emit(row, val)

        def on_slider(ival):
            if self._coord_syncing: return
            val = ival / 10.0
            self._coord_syncing = True
            spin.setValue(val)
            self._coord_syncing = False
            row = self.point_list.currentRow()
            if row >= 0:
                signal.emit(row, val)

        return on_spin, on_slider

    def _connect_coord_handlers(self):
        """Wire spin↔slider sync and signal emission for all three axes."""
        pairs = [
            (self.x_spin, self.x_slider, self.point_x_changed),
            (self.y_spin, self.y_slider, self.point_y_changed),
            (self.z_spin, self.z_slider, self.point_z_changed),
        ]
        for spin, slider, signal in pairs:
            on_spin, on_slider = self._make_coord_handlers(spin, slider, signal)
            spin.valueChanged.connect(on_spin)
            slider.valueChanged.connect(on_slider)

    def _emit_dir_lookat(self):
        self.fixed_point_changed.emit("direction",
            self._dir_lx.value(), self._dir_ly.value(), self._dir_lz.value())

    def _emit_dir_vec(self):
        self.fixed_vector_changed.emit("direction",
            self._dir_vx.value(), self._dir_vy.value(), self._dir_vz.value())

    def _emit_north_vec(self):
        self.fixed_vector_changed.emit("north",
            self._north_vx.value(), self._north_vy.value(), self._north_vz.value())

    def _emit_north_pt(self):
        self.fixed_point_changed.emit("north",
            self._north_px.value(), self._north_py.value(), self._north_pz.value())

    # Public API

    def refresh_point_list(self, layer, pts, selected_idx=-1):
        if layer != self._current_layer:
            return
        self.point_list.blockSignals(True)
        self.point_list.clear()
        for i, p in enumerate(pts):
            item = QListWidgetItem("  %02d   %8.3f  %8.3f  %8.3f" % (i, p[0], p[1], p[2]))
            item.setForeground(QColor(C["text"]))
            self.point_list.addItem(item)
        if 0 <= selected_idx < len(pts):
            self.point_list.setCurrentRow(selected_idx)
            p = pts[selected_idx]
            self._coord_syncing = True
            self.x_spin.setValue(p[0]);  self.x_slider.setValue(int(p[0] * 10))
            self.y_spin.setValue(p[1]);  self.y_slider.setValue(int(p[1] * 10))
            self.z_spin.setValue(p[2]);  self.z_slider.setValue(int(p[2] * 10))
            self._coord_syncing = False
        self.point_list.blockSignals(False)

    def set_mesh_label(self, name):
        self.lbl_mesh.setText(name)

    def set_pointcloud_label(self, name):
        self.lbl_pointcloud.setText(name)

    def load_from_project(self, proj):
        dir_map   = {"tangent": 0, "spline": 1, "look_at": 2, "fixed_vector": 3}
        north_map = {"fixed_vector": 0, "spline": 1, "fixed_point": 2}
        d = proj["direction"]
        self.dir_mode_combo.setCurrentIndex(dir_map.get(d["mode"], 0))
        self._dir_lx.setValue(d["target"][0]); self._dir_ly.setValue(d["target"][1])
        self._dir_lz.setValue(d["target"][2])
        self._dir_vx.setValue(d["vector"][0]); self._dir_vy.setValue(d["vector"][1])
        self._dir_vz.setValue(d["vector"][2])
        n = proj["north"]
        self.north_mode_combo.setCurrentIndex(north_map.get(n["mode"], 0))
        self._north_vx.setValue(n["vector"][0]); self._north_vy.setValue(n["vector"][1])
        self._north_vz.setValue(n["vector"][2])
        self._north_px.setValue(n["target"][0]); self._north_py.setValue(n["target"][1])
        self._north_pz.setValue(n["target"][2])
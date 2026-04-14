"""
NeoPathGen - A Cinematic Path Generator
A tool for designing camera paths and exporting them for renderers.
"""

import sys
import json
from pathlib import Path
import numpy as np

from PyQt5.QtWidgets import (
    QToolBar, QPushButton, QWidget,
    QFrame, QMainWindow, QSizePolicy,
    QStackedWidget, QSplitter, QTabWidget,
    QVBoxLayout, QStatusBar, QMessageBox,
    QFileDialog, QApplication
)
from PyQt5.QtCore import Qt

from vispy import app as vispy_app

from neopathgen.palette import C, SS
from neopathgen.viewport import Viewport3D

from neopathgen.stages.stage_1 import Stage1Panel
from neopathgen.stages.stage_2 import Stage2Panel
from neopathgen.stages.stage_3 import Stage3Panel, SpeedCurveWidget
from neopathgen.stages.stage_4 import Stage4Panel

from neopathgen.utils.helpers import empty_project
from neopathgen.utils.speed_profile import apply_speed_profile
from neopathgen.utils.spline import (
    compute_spline, compute_direction_vectors,
    compute_north_vectors, build_export_lines
)
from neopathgen.utils.stereo import compute_stereo_offset

# ══════════════════════════════════════════════════════════════════════════════
# Top toolbar
# ══════════════════════════════════════════════════════════════════════════════

class TopToolbar(QToolBar):
    def __init__(self, parent=None):
        super(TopToolbar, self).__init__(parent)
        self.setMovable(False)
        self.setFloatable(False)

        def tb(label, icon="", checkable=False):
            b = QPushButton((f"{icon}  {label}") if icon else label)
            b.setProperty("style", "toolbtn")
            b.setCheckable(checkable)
            b.setFixedHeight(30)
            return b

        self.btn_new  = tb("NEW",  "◻")
        self.btn_open = tb("OPEN", "▲")
        self.btn_save = tb("SAVE", "●")
        self.btn_perspective = tb("PERSP", "⬡")
        self.btn_top         = tb("TOP")
        self.btn_front       = tb("FRONT")
        self.btn_side        = tb("SIDE")
        self.btn_grid        = tb("GRID", "⊞", checkable=True)
        self.btn_grid.setChecked(True)
        self.btn_place       = tb("PLACE POINT", "+", checkable=True)
        self.btn_mesh        = tb("MESH", "◈")

        for b in [self.btn_new, self.btn_open, self.btn_save]:
            self.addWidget(b)
        self._sep()
        for b in [self.btn_perspective, self.btn_top,
                  self.btn_front, self.btn_side, self.btn_grid]:
            self.addWidget(b)
        self._sep()
        self.addWidget(self.btn_place)
        sp = QWidget(); sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(sp)
        self.addWidget(self.btn_mesh)

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.VLine)
        f.setStyleSheet(f"color: {C["panel_border"]}; margin: 4px 4px;")
        self.addWidget(f)


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):

    TAB_PLACE  = 0
    TAB_SPLINE = 1
    TAB_SPEED  = 2
    TAB_STEREO = 3

    TAB_DEPS = {
        1: lambda p: len(p["path"]["points"]) >= 2,
        2: lambda p: len(p["path"]["points"]) >= 2,
        3: lambda p: len(p["path"]["points"]) >= 2,
    }

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("NeoPathGen — Camera Path Generator")
        self.resize(1280, 800)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(SS)

        self._project      = empty_project()
        self._project_path = None
        self._dirty        = False

        # Cached spline results
        self._spline_path  = None
        self._spline_dir   = None
        self._spline_north = None

        # Cached re-timed results (Stage 3)
        self._rt_path  = None
        self._rt_dir   = None
        self._rt_north = None

        # Cached stereo results (Stage 4)
        self._stereo_left_path   = None
        self._stereo_left_dir    = None
        self._stereo_left_north  = None
        self._stereo_right_path  = None
        self._stereo_right_dir   = None
        self._stereo_right_north = None

        # Toolbar
        self.toolbar = TopToolbar(self)
        self.addToolBar(self.toolbar)

        # ── Widgets ───────────────────────────────────────────────────────────
        self.viewport = Viewport3D()
        self.panel_s1 = Stage1Panel()
        self.panel_s2 = Stage2Panel()
        self.panel_s3 = Stage3Panel()
        self.panel_s4 = Stage4Panel()
        self._curve_widget = SpeedCurveWidget()

        # ── Layout: tab bar on top, below it a horizontal splitter ───────────
        # The splitter holds:  [left panel stack]  |  [3-D viewport]
        # Switching tabs only swaps which left panel is visible —
        # the viewport stays parented to the splitter permanently.

        self._left_stack = QStackedWidget()
        self._left_stack.addWidget(self.panel_s1)   # index 0 → TAB_PLACE
        self._left_stack.addWidget(self.panel_s2)   # index 1 → TAB_SPLINE
        self._left_stack.addWidget(self.panel_s3)   # index 2 → TAB_SPEED
        self._left_stack.addWidget(self.panel_s4)   # index 3 → TAB_STEREO
        self._left_stack.setFixedWidth(265)

        # Right-side stack: viewport (tabs 0,1,3) or curve editor (tab 2)
        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(self.viewport)      # index 0
        self._right_stack.addWidget(self._curve_widget) # index 1

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.addWidget(self._left_stack)
        self._splitter.addWidget(self._right_stack)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        # Tabs drive the left stack; the tab content widget is just a spacer
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.tabBar().setExpanding(False)
        for label in ["01 · PLACE", "02 · SPLINE", "03 · SPEED", "04 · STEREO"]:
            self.tabs.addTab(QWidget(), label)   # empty — visual only
        self.tabs.setMaximumHeight(self.tabs.tabBar().sizeHint().height() + 2)

        # Outer container: tab bar on top, splitter below
        outer = QWidget()
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(0)
        ol.addWidget(self.tabs)
        ol.addWidget(self._splitter, 1)

        self.setCentralWidget(outer)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._set_status()

        self._wire_toolbar()
        self._wire_stage1()
        self._wire_stage2()
        self._wire_stage3()
        self._wire_stage4()
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_tab(self, left, right, label):
        # Kept for compatibility but no longer used in __init__
        pass

    def _wire_toolbar(self):
        tb = self.toolbar
        tb.btn_new.clicked.connect(self._action_new)
        tb.btn_open.clicked.connect(self._action_open)
        tb.btn_save.clicked.connect(self._action_save)
        tb.btn_perspective.clicked.connect(lambda: self.viewport.set_view_preset("perspective"))
        tb.btn_top.clicked.connect(lambda: self.viewport.set_view_preset("top"))
        tb.btn_front.clicked.connect(lambda: self.viewport.set_view_preset("front"))
        tb.btn_side.clicked.connect(lambda: self.viewport.set_view_preset("side"))
        tb.btn_grid.toggled.connect(self.viewport.set_grid_visible)
        tb.btn_place.toggled.connect(self._on_place_toggled)
        tb.btn_mesh.clicked.connect(self.panel_s1.mesh_load_requested)

    def _wire_stage1(self):
        p = self.panel_s1
        p.layer_changed.connect(self._on_layer_changed)
        p.mode_changed.connect(self._on_mode_changed)
        p.add_point_requested.connect(self._add_point_at_origin)
        p.delete_point_requested.connect(self._delete_selected_point)
        p.clear_all_requested.connect(self._clear_all_points)
        p.point_selected.connect(self._on_point_selected)
        p.point_x_changed.connect(self._on_point_x_changed)
        p.point_y_changed.connect(self._on_point_y_changed)
        p.point_z_changed.connect(self._on_point_z_changed)
        p.fixed_vector_changed.connect(self._on_fixed_vector_changed)
        p.fixed_point_changed.connect(self._on_fixed_point_changed)
        p.mesh_load_requested.connect(self._load_mesh)
        p.mesh_toggle.connect(self.viewport.set_mesh_visible)
        p.pointcloud_load_requested.connect(self._load_pointcloud)
        p.pointcloud_toggle.connect(self.viewport.set_pointcloud_visible)
        self.viewport.point_placed.connect(self._on_point_placed)

    def _wire_stage2(self):
        p = self.panel_s2
        p.generate_requested.connect(self._generate_splines)
        p.export_requested.connect(self._export_path)
        p.resolution_changed.connect(
            lambda v: self._project["spline"].__setitem__("resolution", v))
        p.spline_param_changed.connect(self._on_spline_param_changed)
        p.show_dir_vectors_changed.connect(
            lambda v: self.viewport.set_vector_field_visible("direction", v))
        p.show_north_vectors_changed.connect(
            lambda v: self.viewport.set_vector_field_visible("north", v))
        p.show_spline_changed.connect(self.viewport.set_spline_visible)

    def _on_spline_param_changed(self, layer, key, value):
        if layer == "path":
            self._project["spline"][key] = value
        else:
            self._project[layer][key] = value
        self._mark_dirty()

    def _wire_stage3(self):
        p = self.panel_s3
        p.apply_requested.connect(self._apply_speed_profile)
        p.export_requested.connect(self._export_retimed)
        p.profile_changed.connect(self._on_profile_changed)
        p.show_retimed_changed.connect(self.viewport.set_retimed_visible)

    def _on_profile_changed(self, prof):
        self._project["speed_profile"] = prof
        self._curve_widget.update_curve(prof)
        self._mark_dirty()

    def _apply_speed_profile(self):

        if self._spline_path is None:
            QMessageBox.warning(self, "Not ready",
                "Generate splines in Stage 2 first.")
            return

        prof    = self.panel_s3.get_profile()
        targets = self.panel_s3.get_retime_targets()
        res     = self._project["spline"]["resolution"]

        try:
            rt_path, rt_dir, rt_north, u_samp = apply_speed_profile(
                self._spline_path, self._spline_dir, self._spline_north,
                prof, res)
        except Exception as e:
            self.panel_s3.set_apply_status(False, f"Error: {e}")
            return

        # Apply selectively: arrays whose checkbox is off keep the
        # uniform Stage-2 version (re-sampled at the new u positions
        # so they're still the same length, but without speed warping).
        self._rt_path  = rt_path
        self._rt_dir   = rt_dir   if targets["direction"] else self._spline_dir
        self._rt_north = rt_north if targets["north"]     else self._spline_north

        # Build a readable target summary for the status label
        active = ["path"]
        if targets["direction"]: active.append("dir")
        if targets["north"]:     active.append("north")
        target_str = " + ".join(active)

        self.viewport.set_retimed_path(self._rt_path, u_samp)
        self.panel_s3.set_apply_status(
            True, f"✓  Applied to: {target_str}  ·  {len(prof)} segs  ·  {res} samples"
            )
        self._mark_dirty()

    def _export_retimed(self):
        if self._rt_path is None:
            QMessageBox.warning(self, "Not ready", "Apply speed profile first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Re-timed Path", "path_retimed.txt",
            "Text files (*.txt)")
        if not path:
            return

        try:
            lines = build_export_lines(
                self._rt_path, self._rt_dir, self._rt_north)
            with open(path, "w") as f:
                f.write("\n".join(lines))
            self.panel_s3.set_export_status(
                f"Exported {len(lines)} lines → {Path(path).name}")
            self.status.showMessage(f"Exported → {path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _wire_stage4(self):
        p = self.panel_s4
        p.generate_requested.connect(self._generate_stereo)
        p.export_requested.connect(self._export_stereo)
        p.offset_changed.connect(
            lambda v: self._project.__setitem__("stereo_offset", v))
        p.show_left_changed.connect(
            lambda v: self.viewport.set_stereo_visible("left", v))
        p.show_right_changed.connect(
            lambda v: self.viewport.set_stereo_visible("right", v))

    def _source_arrays(self):
        """
        Return the most-downstream (path, dir, north) available:
        Stage 3 re-timed if present, otherwise Stage 2 uniform.
        """
        if self._rt_path is not None:
            return self._rt_path, self._rt_dir, self._rt_north
        return self._spline_path, self._spline_dir, self._spline_north

    def _generate_stereo(self):
        path, dir_v, north_v = self._source_arrays()
        if path is None:
            QMessageBox.warning(self, "Not ready",
                "Generate splines in Stage 2 first.")
            return

        offset = self._project.get("stereo_offset", 0.1)
        try:
            (self._stereo_left_path,  self._stereo_left_dir,
             self._stereo_left_north,
             self._stereo_right_path, self._stereo_right_dir,
             self._stereo_right_north) = \
                compute_stereo_offset(path, dir_v, north_v, offset)
        except Exception as e:
            self.panel_s4.set_generate_status(False, f"Error: {e}")
            return

        self.viewport.set_stereo_path("left",  self._stereo_left_path)
        self.viewport.set_stereo_path("right", self._stereo_right_path)

        has_rt = self._rt_path is not None
        self.panel_s4.set_source_label(has_rt)
        self.panel_s4.set_generate_status(
            True, f"✓  {len(path)} samples  ·  offset ±{offset * 0.5:.4f}"
            )
        self._mark_dirty()

    def _export_stereo(self):
        if self._stereo_left_path is None:
            QMessageBox.warning(self, "Not ready",
                "Generate stereo offset paths first.")
            return

        base, _ = QFileDialog.getSaveFileName(
            self, "Export Stereo Paths — choose base filename",
            "path.txt", "Text files (*.txt)")
        if not base:
            return

        base_p     = Path(base)
        stem       = base_p.stem
        left_path  = base_p.with_name(stem + "_left.txt")
        right_path = base_p.with_name(stem + "_right.txt")

        try:
            left_lines  = build_export_lines(
                self._stereo_left_path,
                self._stereo_left_dir,
                self._stereo_left_north)
            right_lines = build_export_lines(
                self._stereo_right_path,
                self._stereo_right_dir,
                self._stereo_right_north)
            with open(left_path,  "w") as f: f.write("\n".join(left_lines))
            with open(right_path, "w") as f: f.write("\n".join(right_lines))
            self.panel_s4.set_export_status(
                f"Exported:\n{left_path.name}\n{right_path.name}")
            self.status.showMessage(
                f"Stereo exported → {left_path.name} / {right_path.name}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _action_new(self):
        if self._dirty:
            r = QMessageBox.question(self, "New Project",
                "Discard unsaved changes?", QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes:
                return
        self._project = empty_project()
        self._project_path = None
        self._dirty = False
        self._full_refresh()

    def _action_open(self):
        if self._dirty:
            r = QMessageBox.question(self, "Open Project",
                "Discard unsaved changes?", QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes:
                return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "NeoPathGen JSON (*.npj *.json)")
        if not path: return
        try:
            with open(path) as f:
                self._project = json.load(f)
            self._project_path = Path(path)
            self._dirty = False
            self._full_refresh()
            self.panel_s1.load_from_project(self._project)
            self.panel_s2.load_from_project(self._project)
            self.panel_s3.load_from_project(self._project)
            self.panel_s4.load_from_project(self._project)
            self._curve_widget.update_curve(self._project.get("speed_profile", []))
            self._load_pointcloud(open_project=True)
            self._load_mesh(open_project=True)
            self.status.showMessage(f"Opened {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def _action_save(self):
        if self._project_path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", "project.npj",
                "NeoPathGen JSON (*.npj *.json)")
            if not path: return
            self._project_path = Path(path)
        try:
            with open(self._project_path, "w") as f:
                json.dump(self._project, f, indent=2)
            self._dirty = False
            self.status.showMessage(f"Saved → {self._project_path}" , 4000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")

    # ── Place mode

    def _on_place_toggled(self, checked):
        self.viewport.set_place_mode(checked)
        self.status.showMessage(
            "Click on the grid to place a point"
            if checked else "Place mode off", 3000)

    def _on_point_placed(self, layer, x, y):
        pts = self._project[layer]["points"]
        pts.append([round(x, 4), round(y, 4), 0.0])
        self._mark_dirty()
        self._refresh_layer(layer)
        idx = len(pts) - 1
        self.panel_s1.refresh_point_list(layer, pts, idx)
        self.viewport.set_selected_point(layer, idx, pts)
        self._set_status()

    # ── Layer / mode

    def _on_layer_changed(self, layer):
        self.viewport.set_active_layer(layer)
        pts = self._project[layer]["points"]
        self.panel_s1.refresh_point_list(layer, pts)

    def _on_mode_changed(self, which, mode):
        self._project[which]["mode"] = mode
        self._mark_dirty()

    def _on_fixed_vector_changed(self, which, x, y, z):
        self._project[which]["vector"] = [x, y, z]
        self._mark_dirty()

    def _on_fixed_point_changed(self, which, x, y, z):
        self._project[which]["target"] = [x, y, z]
        self._mark_dirty()

    # ── Point operations

    def _active_layer(self):
        return ["path", "direction", "north"][self.panel_s1.layer_combo.currentIndex()]

    def _add_point_at_origin(self):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        if pts:
            last = pts[-1]
            pts.append([last[0] + 1.0, last[1], last[2]])
        else:
            pts.append([0.0, 0.0, 0.0])
        self._mark_dirty()
        self._refresh_layer(layer)
        self.panel_s1.refresh_point_list(layer, pts, len(pts) - 1)
        self.viewport.set_selected_point(layer, len(pts) - 1, pts)

    def _delete_selected_point(self):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        row   = self.panel_s1.point_list.currentRow()
        if row < 0 or row >= len(pts): return
        pts.pop(row)
        self._mark_dirty()
        self._refresh_layer(layer)
        new_row = min(row, len(pts) - 1)
        self.panel_s1.refresh_point_list(layer, pts, new_row)
        self.viewport.set_selected_point(layer, new_row, pts)

    def _clear_all_points(self):
        layer = self._active_layer()
        r = QMessageBox.question(self, "Clear All",
            f"Remove all {layer} control points?" ,
            QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes: return
        self._project[layer]["points"] = []
        self._mark_dirty()
        self._refresh_layer(layer)
        self.panel_s1.refresh_point_list(layer, [])
        self.viewport.set_selected_point(layer, -1, [])

    def _on_point_selected(self, idx):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        self.viewport.set_selected_point(layer, idx, pts)
        self.panel_s1.refresh_point_list(layer, pts, idx)

    def _on_point_x_changed(self, idx, x):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        if 0 <= idx < len(pts):
            pts[idx][0] = round(x, 4)
            self._mark_dirty()
            self._refresh_layer(layer)
            self.panel_s1.refresh_point_list(layer, pts, idx)
            self.viewport.set_selected_point(layer, idx, pts)

    def _on_point_y_changed(self, idx, y):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        if 0 <= idx < len(pts):
            pts[idx][1] = round(y, 4)
            self._mark_dirty()
            self._refresh_layer(layer)
            self.panel_s1.refresh_point_list(layer, pts, idx)
            self.viewport.set_selected_point(layer, idx, pts)

    def _on_point_z_changed(self, idx, z):
        layer = self._active_layer()
        pts   = self._project[layer]["points"]
        if 0 <= idx < len(pts):
            pts[idx][2] = round(z, 4)
            self._mark_dirty()
            self._refresh_layer(layer)
            self.panel_s1.refresh_point_list(layer, pts, idx)
            self.viewport.set_selected_point(layer, idx, pts)

    # ── Spline generation & export

    def _generate_splines(self):
        sp  = self._project["spline"]
        res = sp["resolution"]

        # Clear previous results
        self._spline_path  = None
        self._spline_dir   = None
        self._spline_north = None
        for layer in ("path", "direction", "north"):
            self.viewport.set_spline(layer, None)
        self.viewport.set_vector_field("direction", None)
        self.viewport.set_vector_field("north", None)

        # ── Path (mandatory) ──────────────────────────────────────────────────
        try:
            self._spline_path = compute_spline(
                self._project["path"]["points"],
                res, sp["smoothness"], sp["closed"])
        except Exception as e:
            self.panel_s2.set_generate_status(False, f"Path error: {e}")
            return
        self.viewport.set_spline("path", self._spline_path)

        # ── Direction ─────────────────────────────────────────────────────────
        dir_cfg = self._project["direction"]
        if dir_cfg["mode"] == "spline":
            try:
                raw = compute_spline(
                    dir_cfg["points"], res,
                    dir_cfg.get("smoothness", 0.0),
                    dir_cfg.get("closed", False))
                # raw contains world-space positions on the direction spline.
                # The direction vector at each sample is the unit vector FROM
                # the corresponding path point TOWARD the direction spline point.
                diff  = raw - self._spline_path
                norms = np.linalg.norm(diff, axis=1, keepdims=True)
                self._spline_dir = diff / np.where(norms < 1e-12, 1.0, norms)
                self.viewport.set_spline("direction", raw)
            except Exception as e:
                self.panel_s2.set_generate_status(
                    False, f"Direction spline error: {e}")
                return
        else:
            try:
                self._spline_dir = compute_direction_vectors(
                    self._spline_path, dir_cfg, res)
            except Exception as e:
                self.panel_s2.set_generate_status(
                    False, f"Direction vector error: {e}")
                return

        # ── North ─────────────────────────────────────────────────────────────
        north_cfg = self._project["north"]
        if north_cfg["mode"] == "spline":
            try:
                raw = compute_spline(
                    north_cfg["points"], res,
                    north_cfg.get("smoothness", 0.0),
                    north_cfg.get("closed", False))
                # Same logic: unit vector from path point toward north spline point.
                diff  = raw - self._spline_path
                norms = np.linalg.norm(diff, axis=1, keepdims=True)
                self._spline_north = diff / np.where(norms < 1e-12, 1.0, norms)
                self.viewport.set_spline("north", raw)
            except Exception as e:
                self.panel_s2.set_generate_status(
                    False, f"North spline error: {e}")
                return
        else:
            try:
                self._spline_north = compute_north_vectors(
                    self._spline_path, north_cfg, res)
            except Exception as e:
                self.panel_s2.set_generate_status(
                    False, f"North vector error: {e}")
                return

        # ── Update vector field visuals ───────────────────────────────────────
        self.viewport.set_vector_field("direction", self._spline_path,
                                       self._spline_dir)
        self.viewport.set_vector_field("north",     self._spline_path,
                                       self._spline_north)

        self.panel_s2.set_generate_status(
            True, f"✓  {res} samples  ·  path + dir + north ready")
        self._mark_dirty()

    def _export_path(self):
        if self._spline_path is None:
            QMessageBox.warning(self, "Not ready", "Generate the splines first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Path", "path.txt", "Text files (*.txt)")
        if not path:
            return

        try:
            lines = build_export_lines(
                self._spline_path, self._spline_dir, self._spline_north)
            with open(path, "w") as f:
                f.write("\n".join(lines))
            self.panel_s2.set_export_status(
                f"Exported {len(lines)} lines → {Path(path).name}")
            self.status.showMessage(f"Exported → {path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # ── Mesh

    def _load_mesh(self, open_project=False):
        if not open_project:
            path, _ = QFileDialog.getOpenFileName(
                self, "Load Reference Mesh", "", "Mesh files (*.obj *.ply *.stl)")
            if not path:
                return
            self._project["mesh_path"] = path
        else:
            path = self._project["mesh_path"]
            if not path:
                return

        result = self.viewport.load_mesh(path)
        if result is True:
            name = Path(path).name
            self.panel_s1.set_mesh_label(name)
            
            self.status.showMessage(f"Mesh loaded: {name}", 3000)
        else:
            QMessageBox.critical(self, "Mesh Error",
                f"Could not load mesh (is trimesh installed?):\n{result}")

    # ── Mesh

    def _load_pointcloud(self, open_project=False):

        if not open_project:
            path, _ = QFileDialog.getOpenFileName(
                self, "Load Point Cloud", "", "Binary point cloud (*.bin)")
            if not path:
                return
            self._project["pointcloud_path"] = path
        else:
            path = self._project["pointcloud_path"]
            if not path:
                return
        try:
            xyz, t = self.viewport.load_pointcloud(path)
            self.viewport.set_pointcloud(xyz, t)
            name = Path(path).name
            self.panel_s1.set_pointcloud_label(
                f"{name}  ({len(xyz):,})")
            self.status.showMessage(
                f"Point cloud loaded: {name} — {len(xyz):,} points", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Point Cloud Error",
                f"Could not load point cloud:\n{e}")

    # ── Tab gating

    def _on_tab_changed(self, idx):
        # Swap left panel
        self._left_stack.setCurrentIndex(idx)

        # Swap right panel: curve editor on Speed tab, viewport everywhere else
        self._right_stack.setCurrentIndex(1 if idx == self.TAB_SPEED else 0)

        if idx == self.TAB_PLACE:
            # Re-assert selection ring in case it was cleared by another tab
            layer = self._active_layer()
            pts   = self._project[layer]["points"]
            row   = self.panel_s1.point_list.currentRow()
            self.viewport.set_selected_point(layer, row, pts)

        if idx == self.TAB_SPLINE:
            self.panel_s2.refresh_layer_info(self._project)

        if idx == self.TAB_SPEED:
            # Refresh curve with current profile
            self._curve_widget.update_curve(
                self._project.get("speed_profile", []))

        if idx == self.TAB_STEREO:
            self.panel_s4.set_source_label(self._rt_path is not None)
            self.panel_s4.load_from_project(self._project)

        dep = self.TAB_DEPS.get(idx)
        if dep and not dep(self._project):
            r = QMessageBox.warning(self, "Incomplete Data",
                "This stage requires at least 2 path control points.\n"
                "Continue anyway?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel)
            if r != QMessageBox.Yes:
                self.tabs.blockSignals(True)
                self.tabs.setCurrentIndex(self.TAB_PLACE)
                self._left_stack.setCurrentIndex(self.TAB_PLACE)
                self._right_stack.setCurrentIndex(0)
                self.tabs.blockSignals(False)

    # ── Helpers

    def _refresh_layer(self, layer):
        pts = self._project[layer]["points"]
        self.viewport.set_control_points(layer, pts)
        self.viewport.set_spline(layer, None)

    def _full_refresh(self):
        for layer in ("path", "direction", "north"):
            self._refresh_layer(layer)
        layer = self._active_layer()
        self.panel_s1.refresh_point_list(layer, self._project[layer]["points"])
        self.panel_s2.refresh_layer_info(self._project)
        # Clear cached splines — they belong to old project data
        self._spline_path = self._spline_dir = self._spline_north = None
        self._rt_path = self._rt_dir = self._rt_north = None
        self._stereo_left_path = self._stereo_right_path = None
        self._stereo_left_dir  = self._stereo_right_dir  = None
        self._stereo_left_north = self._stereo_right_north = None
        self.viewport.set_vector_field("direction", None)
        self.viewport.set_vector_field("north", None)
        self.viewport.set_retimed_path(None, None)
        self.viewport.set_stereo_path("left",  None)
        self.viewport.set_stereo_path("right", None)
        self.panel_s2.set_generate_status(False, "No spline generated")
        self.panel_s3.set_apply_status(False, "No profile applied yet.")
        self.panel_s4.set_generate_status(False, "No offset generated.")
        self._set_status()

    def _mark_dirty(self):
        self._dirty = True
        self._set_status()

    def _set_status(self):
        n_path = len(self._project["path"]["points"])
        n_dir  = len(self._project["direction"]["points"])
        n_nor  = len(self._project["north"]["points"])
        fname  = self._project_path.name if self._project_path else "unsaved"
        dirty  = " ●" if self._dirty else ""
        self.status.showMessage(
            f"{fname}{dirty}  ·  path: {n_path} pts  ·  dir: {n_dir} pts  ·  north: {n_nor} pts  ·  "
            "orbit: LMB   zoom: RMB/scroll    move center: SHIFT + LMB   change FOV: SHIFT + RMB"
        )

    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()

        # ── File
        if mods == Qt.ControlModifier:
            if key == Qt.Key_S:
                self._action_save()
                return
            if key == Qt.Key_O:
                self._action_open()
                return
            if key == Qt.Key_N:
                self._action_new()
                return
            if key == Qt.Key_Z:
                # placeholder for undo
                return

        # ── Tabs
        if key == Qt.Key_1: self.tabs.setCurrentIndex(0); return
        if key == Qt.Key_2: self.tabs.setCurrentIndex(1); return
        if key == Qt.Key_3: self.tabs.setCurrentIndex(2); return
        if key == Qt.Key_4: self.tabs.setCurrentIndex(3); return

        # ── Stage 1 shortcuts (only active on the Place tab)
        if self.tabs.currentIndex() == self.TAB_PLACE and mods == Qt.ControlModifier:
            if key == Qt.Key_A:
                self._add_point_at_origin()
                return
            if key == Qt.Key_D:
                self._delete_selected_point()
                return
            if key == Qt.Key_R:
                self._generate_splines()
                self._apply_speed_profile()
                self._generate_stereo()
                return
            if key == Qt.Key_Tab:
                current = self.panel_s1.layer_combo.currentIndex()
                self.panel_s1.layer_combo.setCurrentIndex((current + 1) % 3)
                return
            if key == Qt.Key_P:
                self.toolbar.btn_place.toggle()
                return

        # ── Stage 2
        if self.tabs.currentIndex() == self.TAB_SPLINE and mods == Qt.ControlModifier:
            if key == Qt.Key_G:
                self._generate_splines()
                return
            if key == Qt.Key_E:
                self._export_path()
                return

        # ── Stage 3
        if self.tabs.currentIndex() == self.TAB_SPEED and mods == Qt.ControlModifier:
            if key == Qt.Key_A:
                self.panel_s3._add_segment()
                return
            if key == Qt.Key_D:
                self.panel_s3._delete_segment()
                return
            if key == Qt.Key_G:
                self._apply_speed_profile()
                return
            if key == Qt.Key_E:
                self._export_retimed()
                return
        
        # ── Stage 4
        if self.tabs.currentIndex() == self.TAB_STEREO and mods == Qt.ControlModifier:
            if key == Qt.Key_G:
                self._generate_stereo()
                return
            if key == Qt.Key_E:
                self._export_stereo()
                return

        # ── Viewport camera presets (work on any tab with the viewport visible)
        if self.tabs.currentIndex() != self.TAB_SPEED:
            if key == Qt.Key_6:
                self.viewport.set_view_preset("perspective"); return
            if key == Qt.Key_7:
                self.viewport.set_view_preset("top"); return
            if key == Qt.Key_8 and mods == Qt.NoModifier:
                self.viewport.set_view_preset("front"); return
            if key == Qt.Key_9:
                self.viewport.set_view_preset("side"); return

        super(MainWindow, self).keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    vispy_app.use_app("pyqt5")
    app = QApplication(sys.argv)
    app.setApplicationName("NeoPathGen")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
# ══════════════════════════════════════════════════════════════════════════════
# 3-D Viewport
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np
import trimesh

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

import vispy.scene
from vispy.scene import SceneCanvas, visuals
from vispy.scene.cameras import TurntableCamera
from vispy import app as vispy_app

from neopathgen.palette import *

def _grid_lines(extent=20, step=1):
    lines = []
    for c in np.arange(-extent, extent + step, step):
        lines += [[c, -extent, 0], [c,  extent, 0]]
        lines += [[-extent, c, 0], [ extent, c, 0]]
    return np.array(lines, dtype=np.float32)


class Viewport3D(QWidget):
    point_placed = pyqtSignal(str, float, float)

    def __init__(self, parent=None):
        super(Viewport3D, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._active_layer = "path"
        self._place_mode   = False

        # Canvas
        self.canvas = SceneCanvas(keys="interactive", bgcolor=(0.03, 0.03, 0.06, 1.0))
        self.canvas.native.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.events.mouse_press.connect(self._on_mouse_press)

        # View
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = TurntableCamera(fov=45, elevation=28,
                                           azimuth=-50, distance=18, up="+z")
        self.scene = self.view.scene

        # Grid
        gv = _grid_lines(20, 1)
        gc = np.full((len(gv), 4), [0.12, 0.12, 0.20, 0.6], dtype=np.float32)
        for i in range(0, len(gv), 2):
            v = gv[i]
            if abs(v[0]) % 5 < 0.01 or abs(v[1]) % 5 < 0.01:
                gc[i] = gc[i+1] = [0.18, 0.18, 0.30, 0.9]
        self.grid_vis = visuals.Line(pos=gv, color=gc,
                                     connect="segments", parent=self.scene)

        # Axis
        L = 2.5
        ax_v = np.array([[0,0,0],[L,0,0],[0,0,0],[0,L,0],[0,0,0],[0,0,L]],
                         dtype=np.float32)
        ax_c = np.array([[.95,.25,.25,1],[.95,.25,.25,1],
                         [.25,.95,.35,1],[.25,.95,.35,1],
                         [.30,.55,1.0,1],[.30,.55,1.0,1]], dtype=np.float32)
        self.axis_vis = visuals.Line(pos=ax_v, color=ax_c, connect="segments",
                                     width=2, parent=self.scene)

        # Per-layer visuals
        self._cp_vis   = {}
        self._line_vis = {}
        self._sel_vis  = {}

        for layer in ("path", "direction", "north"):
            fc = LAYER_COLOR[layer]
            sc = LAYER_SPLINE_COLOR[layer]

            mk = visuals.Markers(parent=self.scene)
            mk.set_data(np.zeros((1, 3), dtype=np.float32),
                        face_color=(fc[0], fc[1], fc[2], 0.0), size=1)
            self._cp_vis[layer] = mk

            ln = visuals.Line(pos=np.zeros((2, 3), dtype=np.float32),
                              color=(sc[0], sc[1], sc[2], 0.0),
                              width=2, connect="strip", parent=self.scene)
            self._line_vis[layer] = ln

            sel = visuals.Markers(parent=self.scene)
            sel.set_data(np.zeros((1, 3), dtype=np.float32),
                         face_color=(1, 1, 1, 0.0), size=1)
            self._sel_vis[layer] = sel

        self._mesh_vis = None

        # Vector field visuals (direction & north arrows)
        # Each is a Line with connect="segments": pairs (tail, head)
        self._vec_vis = {}
        for layer in ("direction", "north"):
            sc = LAYER_SPLINE_COLOR[layer]
            vv = visuals.Line(
                pos=np.zeros((2, 3), dtype=np.float32),
                color=(sc[0], sc[1], sc[2], 0.0),
                connect="segments", width=1, parent=self.scene)
            self._vec_vis[layer] = vv

        # Re-timed path dot cloud (Stage 3)
        self._rt_vis = visuals.Markers(parent=self.scene)
        self._rt_vis.set_data(np.zeros((1, 3), dtype=np.float32),
                              face_color=(1, 1, 1, 0.0), size=1)

        # Stereo offset path lines (Stage 4): left=amber, right=teal
        stereo_colors = {
            "left":  LAYER_SPLINE_COLOR["direction"],   # amber
            "right": LAYER_SPLINE_COLOR["north"],       # teal
        }
        self._stereo_vis = {}
        for side, col in stereo_colors.items():
            ln = visuals.Line(
                pos=np.zeros((2, 3), dtype=np.float32),
                color=(col[0], col[1], col[2], 0.0),
                width=2, connect="strip", parent=self.scene)
            self._stereo_vis[side] = ln

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas.native)

    # Public API

    def set_active_layer(self, layer):
        self._active_layer = layer

    def set_place_mode(self, enabled):
        self._place_mode = enabled
        cur = Qt.CrossCursor if enabled else Qt.ArrowCursor
        self.canvas.native.setCursor(cur)

    def set_grid_visible(self, v):
        self.grid_vis.visible = v
        self.canvas.update()

    def set_control_points(self, layer, pts):
        vis = self._cp_vis[layer]
        fc  = LAYER_COLOR[layer]
        if not pts:
            vis.set_data(np.zeros((1, 3), dtype=np.float32),
                         face_color=(fc[0], fc[1], fc[2], 0.0), size=1)
        else:
            arr = np.array(pts, dtype=np.float32)
            vis.set_data(arr, face_color=fc,
                         edge_color=(1, 1, 1, 0.4), edge_width=1, size=12)
        self.canvas.update()

    def set_selected_point(self, layer, idx, pts):
        sel = self._sel_vis[layer]
        if idx < 0 or idx >= len(pts):
            sel.set_data(np.zeros((1, 3), dtype=np.float32),
                         face_color=(1, 1, 1, 0.0), size=1)
        else:
            p = np.array([pts[idx]], dtype=np.float32)
            sel.set_data(p, face_color=(1, 1, 1, 0.0),
                         edge_color=(1, 1, 1, 0.9), edge_width=2, size=22)
        self.canvas.update()

    def set_spline(self, layer, pts):
        ln = self._line_vis[layer]
        sc = LAYER_SPLINE_COLOR[layer]
        if pts is None or len(pts) < 2:
            ln.set_data(pos=np.zeros((2, 3), dtype=np.float32),
                        color=(sc[0], sc[1], sc[2], 0.0))
        else:
            ln.set_data(pos=pts.astype(np.float32),
                        color=(sc[0], sc[1], sc[2], 0.85))
        self.canvas.update()

    def set_spline_visible(self, layer, v):
        if layer in self._line_vis:
            self._line_vis[layer].visible = v
            self.canvas.update()

    def set_view_preset(self, preset):
        cam = self.view.camera
        presets = {
            "perspective": (28, -50, 18),
            "top":         (90,   0, 22),
            "front":       ( 0,   0, 22),
            "side":        ( 0, -90, 22),
        }
        if preset in presets:
            cam.elevation, cam.azimuth, cam.distance = presets[preset]
        self.canvas.update()

    def load_mesh(self, path):
        try:
            mesh = trimesh.load(path, force="mesh")
            verts = np.array(mesh.vertices, dtype=np.float32)
            faces = np.array(mesh.faces, dtype=np.uint32)
            edges = set()
            for f in faces:
                for i in range(3):
                    e = tuple(sorted((int(f[i]), int(f[(i+1) % 3]))))
                    edges.add(e)
            seg_pts = []
            for a, b in edges:
                seg_pts.append(verts[a]); seg_pts.append(verts[b])
            seg_arr = np.array(seg_pts, dtype=np.float32)
            if self._mesh_vis is not None:
                self._mesh_vis.parent = None
            self._mesh_vis = visuals.Line(
                pos=seg_arr, color=(0.3, 0.3, 0.45, 0.35),
                connect="segments", parent=self.scene)
            self.canvas.update()
            return True
        except Exception as e:
            return str(e)

    def set_mesh_visible(self, v):
        if self._mesh_vis is not None:
            self._mesh_vis.visible = v
            self.canvas.update()

    def set_vector_field(self, layer, path_pts, vec=None, stride=20, scale=0.5):
        """
        Draw evenly-spaced arrows along path_pts pointing in direction vec.

        Parameters
        ----------
        layer     : "direction" or "north"
        path_pts  : (N, 3) ndarray of sample positions, or None to clear
        vec       : (N, 3) ndarray of unit vectors, or None to clear
        stride    : draw one arrow every `stride` samples
        scale     : arrow length in world units
        """
        vv = self._vec_vis[layer]
        sc = LAYER_SPLINE_COLOR[layer]

        if path_pts is None or vec is None or len(path_pts) < 2:
            vv.set_data(pos=np.zeros((2, 3), dtype=np.float32),
                        color=(sc[0], sc[1], sc[2], 0.0))
            self.canvas.update()
            return

        idx    = np.arange(0, len(path_pts), stride)
        tails  = path_pts[idx].astype(np.float32)
        heads  = (path_pts[idx] + vec[idx] * scale).astype(np.float32)

        # Interleave tails and heads: [t0, h0, t1, h1, ...]
        segs = np.empty((len(idx) * 2, 3), dtype=np.float32)
        segs[0::2] = tails
        segs[1::2] = heads

        vv.set_data(pos=segs, color=(sc[0], sc[1], sc[2], 0.85))
        self.canvas.update()

    def set_vector_field_visible(self, layer, v):
        if layer in self._vec_vis:
            self._vec_vis[layer].visible = v
            self.canvas.update()

    def set_retimed_path(self, pts):
        """
        Show the re-timed path as a dot cloud so sample density is visible.
        pts: (N, 3) ndarray or None to clear.
        """
        if pts is None or len(pts) == 0:
            self._rt_vis.set_data(np.zeros((1, 3), dtype=np.float32),
                                  face_color=(1, 1, 1, 0.0), size=1)
        else:
            # Subsample for performance if very dense
            stride = max(1, len(pts) // 2000)
            sub = pts[::stride].astype(np.float32)
            self._rt_vis.set_data(sub,
                                  face_color=(1.0, 0.85, 0.2, 0.7),
                                  size=4, edge_width=0)
        self.canvas.update()

    def set_retimed_visible(self, v):
        self._rt_vis.visible = v
        self.canvas.update()

    def set_stereo_path(self, side, pts):
        """
        side : "left" or "right"
        pts  : (N, 3) ndarray or None to clear.
        """
        ln  = self._stereo_vis[side]
        col = LAYER_SPLINE_COLOR["direction"] if side == "left" \
              else LAYER_SPLINE_COLOR["north"]
        if pts is None or len(pts) < 2:
            ln.set_data(pos=np.zeros((2, 3), dtype=np.float32),
                        color=(col[0], col[1], col[2], 0.0))
        else:
            ln.set_data(pos=pts.astype(np.float32),
                        color=(col[0], col[1], col[2], 0.85))
        self.canvas.update()

    def set_stereo_visible(self, side, v):
        if side in self._stereo_vis:
            self._stereo_vis[side].visible = v
            self.canvas.update()

    # Mouse

    def _on_mouse_press(self, event):
        if not self._place_mode or event.button != 1:
            return
        pos = self._ray_z0(event.pos)
        if pos is not None:
            self.point_placed.emit(self._active_layer, float(pos[0]), float(pos[1]))

    def _ray_z0(self, screen_pos):
        """
        Unproject a screen pixel to world-space (x, y) on the Z=0 plane.

        Vispy's TurntableCamera exposes `transform` which maps from the
        camera's clip/NDC space to scene space.  We instead use the cleaner
        path: ask the scene's node_transform from the *canvas* node down to
        the *view.scene* node, which gives us a full canvas-pixel → world
        transform, then sample it at two different Z depths to build a ray.

        The key insight is that we must pass *canvas* coordinates (pixels),
        not NDC.  Vispy handles the viewport/projection internally.
        """
        try:
            sx, sy = float(screen_pos[0]), float(screen_pos[1])

            # node_transform(B, A) gives the transform that maps A → B.
            # We want canvas-pixel space → scene (world) space.
            tr = self.view.scene.node_transform(self.canvas.scene)

            # Sample two depths along the ray.  In Vispy's canvas→scene
            # transform, Z=0 is the near plane and Z=1 is the far plane.
            p0 = tr.map([sx, sy, 0.0, 1.0])
            p1 = tr.map([sx, sy, 1.0, 1.0])

            # Homogeneous divide
            p0 = p0[:3] / p0[3] if abs(p0[3]) > 1e-12 else p0[:3]
            p1 = p1[:3] / p1[3] if abs(p1[3]) > 1e-12 else p1[:3]

            # Ray–plane intersection at Z = 0
            dz = p1[2] - p0[2]
            if abs(dz) < 1e-9:
                return None      # ray is parallel to the ground plane
            t  = -p0[2] / dz
            xw = p0[0] + t * (p1[0] - p0[0])
            yw = p0[1] + t * (p1[1] - p0[1])
            return xw, yw
        except Exception:
            return None
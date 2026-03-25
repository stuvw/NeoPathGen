# ══════════════════════════════════════════════════════════════════════════════
# Project data model
# ══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLabel, QWidget, 
    QDoubleSpinBox, QHBoxLayout
)
from neopathgen.palette import *

def empty_project():
    return {
        "path": {"points": []},
        "direction": {
            "mode":       "tangent",
            "points":     [],
            "target":     [0.0, 0.0, 0.0],
            "vector":     [0.0, 0.0, 1.0],
            "smoothness": 0.0,
            "closed":     False,
        },
        "north": {
            "mode":       "fixed_vector",
            "points":     [],
            "target":     [0.0, 0.0, 0.0],
            "vector":     [0.0, 0.0, 1.0],
            "smoothness": 0.0,
            "closed":     False,
        },
        "spline": {
            "resolution": 500,
            "smoothness": 0.0,
            "closed":     False,
        },
        "speed_profile": [],
        "stereo_offset": 0.1,
        "mesh_path": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# UI helpers
# ══════════════════════════════════════════════════════════════════════════════

def btn(label, style="", icon=""):
    text = "%s  %s" % (icon, label) if icon else label
    b = QPushButton(text)
    if style:
        b.setProperty("style", style)
    return b

def sec_label(text):
    l = QLabel(text)
    l.setObjectName("SectionLabel")
    return l

def hdivider():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color: %s; margin: 2px 0;" % C["panel_border"])
    return f

def xyz_spinboxes(lo=-9999.0, hi=9999.0):
    boxes = []
    for _ in range(3):
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setSingleStep(0.1)
        sb.setDecimals(3)
        sb.setFixedWidth(74)
        boxes.append(sb)
    return tuple(boxes)

def xyz_row(label_text, lo=-9999.0, hi=9999.0):
    row = QWidget()
    hl  = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(3)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(14)
    lbl.setStyleSheet("color: %s; font-size: 10px;" % C["text_muted"])
    sx, sy, sz = xyz_spinboxes(lo, hi)
    hl.addWidget(lbl)
    hl.addWidget(sx); hl.addWidget(sy); hl.addWidget(sz)
    return row, sx, sy, sz
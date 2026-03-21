import sys
import json
import numpy as np
from pathlib import Path

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

import trimesh

import vispy.scene
from vispy.scene import SceneCanvas, visuals
from vispy.scene.cameras import TurntableCamera
from vispy import app as vispy_app

from scipy.interpolate import splprep, splev

from neopathgen.palette import *
from neopathgen.viewport import *

from neopathgen.stages.stage_1 import *
from neopathgen.stages.stage_2 import *
from neopathgen.stages.stage_3 import *
from neopathgen.stages.stage_4 import *

from neopathgen.utils.helpers import *
from neopathgen.utils.speed_profile import *
from neopathgen.utils.spline import *
from neopathgen.utils.stereo import *
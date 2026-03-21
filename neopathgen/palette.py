# ══════════════════════════════════════════════════════════════════════════════
# Palette & Stylesheet
# ══════════════════════════════════════════════════════════════════════════════

C = {
    "bg":           "#0d0d0f",
    "panel":        "#13131a",
    "panel_border": "#1e1e2e",
    "surface":      "#1a1a26",
    "surface2":     "#22223a",
    "accent":       "#5c7cfa",
    "accent_dim":   "#3a4fa8",
    "danger":       "#f05252",
    "danger_dim":   "#8c2a2a",
    "success":      "#3ecf8e",
    "success_dim":  "#1a6b4a",
    "warning":      "#f7b731",
    "text":         "#e0e0f0",
    "text_dim":     "#7a7a9a",
    "text_muted":   "#44445a",
    "col_path":      "#5c7cfa",
    "col_direction": "#f7b731",
    "col_north":     "#3ecf8e",
}

LAYER_COLOR = {
    "path":      (0.36, 0.49, 0.98, 1.0),
    "direction": (0.97, 0.72, 0.19, 1.0),
    "north":     (0.24, 0.81, 0.56, 1.0),
}
LAYER_SPLINE_COLOR = {
    "path":      (0.36, 0.49, 0.98, 0.85),
    "direction": (0.97, 0.72, 0.19, 0.85),
    "north":     (0.24, 0.81, 0.56, 0.85),
}

SS = """
QMainWindow, QWidget {{
    background-color: {bg};
    color: {text};
    font-family: "Courier New", monospace;
    font-size: 11px;
}}
QToolBar {{
    background-color: {panel};
    border-bottom: 1px solid {panel_border};
    spacing: 4px;
    padding: 4px 8px;
}}
QStatusBar {{
    background-color: {panel};
    border-top: 1px solid {panel_border};
    color: {text_dim};
    font-size: 11px;
    padding: 2px 8px;
}}
QTabWidget::pane {{ border: none; background: {bg}; }}
QTabBar {{ background: {panel}; }}
QTabBar::tab {{
    background: {panel};
    color: {text_dim};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
    font-size: 10px;
    letter-spacing: 2px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    color: {text};
    border-bottom: 2px solid {accent};
    background: {bg};
}}
QTabBar::tab:hover:!selected {{
    color: {text};
    background: {surface};
}}
QGroupBox {{
    color: {text_muted};
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 2px;
    border: 1px solid {panel_border};
    border-radius: 3px;
    margin-top: 10px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 8px;
}}
QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {{
    background: {surface};
    color: {text};
    border: 1px solid {panel_border};
    border-radius: 2px;
    padding: 3px 6px;
    font-family: "Courier New", monospace;
    font-size: 11px;
}}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
    border-color: {accent};
}}
QComboBox QAbstractItemView {{
    background: {surface2};
    color: {text};
    selection-background-color: {accent_dim};
}}
QComboBox::drop-down {{ border: none; }}
QListWidget {{
    background: {surface};
    border: 1px solid {panel_border};
    border-radius: 2px;
    color: {text};
    outline: none;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-bottom: 1px solid {panel_border};
}}
QListWidget::item:selected {{
    background: {accent_dim};
    color: {text};
}}
QListWidget::item:hover:!selected {{ background: {surface2}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {panel};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {surface2};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSlider::groove:horizontal {{
    height: 4px;
    background: {surface2};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{ background: {accent_dim}; border-radius: 2px; }}
QCheckBox {{ spacing: 6px; color: {text_dim}; }}
QCheckBox::indicator {{
    width: 13px; height: 13px;
    background: {surface};
    border: 1px solid {panel_border};
    border-radius: 2px;
}}
QCheckBox::indicator:checked {{
    background: {accent_dim};
    border-color: {accent};
}}
QLabel#AppTitle {{
    color: {text};
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 4px;
}}
QLabel#SectionLabel {{
    color: {text_muted};
    font-size: 9px;
    letter-spacing: 3px;
    font-weight: bold;
    padding: 6px 0 2px 0;
}}
QPushButton {{
    background: transparent;
    color: {text_dim};
    border: 1px solid {panel_border};
    border-radius: 3px;
    padding: 6px 12px;
    font-family: "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 1px;
    text-align: left;
}}
QPushButton:hover {{ background: {surface}; color: {text}; border-color: {surface2}; }}
QPushButton:pressed {{ background: {surface2}; }}
QPushButton[style="primary"] {{
    background: {accent_dim}; color: {text}; border-color: {accent};
}}
QPushButton[style="primary"]:hover {{ background: {accent}; }}
QPushButton[style="danger"] {{
    color: {danger}; border-color: {danger_dim};
}}
QPushButton[style="danger"]:hover {{ background: {danger_dim}; color: {text}; }}
QPushButton[style="success"] {{
    background: {success_dim}; color: {success}; border-color: {success};
}}
QPushButton[style="success"]:hover {{ background: {success}; color: {bg}; }}
QPushButton[style="toolbtn"] {{
    border-color: transparent; padding: 5px 12px;
}}
QPushButton[style="toolbtn"]:hover {{ background: {surface}; border-color: {panel_border}; }}
QPushButton[style="toolbtn"]:checked {{
    background: {accent_dim}; color: {accent}; border-color: {accent};
}}
QSplitter::handle {{ background: {panel_border}; }}
""".format(**C)
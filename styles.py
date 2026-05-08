from PySide6.QtWidgets import QApplication

THEMES = {
    "light": {
        "bg":             "#F5F5F5",
        "surface":        "#FFFFFF",
        "surface2":       "#FAFAFA",
        "border":         "#E0E0E0",
        "text":           "#212121",
        "text_secondary": "#757575",
        "accent":         "#1976D2",
        "accent_hover":   "#1565C0",
        "accent_light":   "#E3F2FD",
        "hover":          "#E8F0FE",
        "selected":       "#C5D9F7",
        "scrollbar_bg":   "#EEEEEE",
        "scrollbar_h":    "#BDBDBD",
        "tag_bg":         "#1976D2",
        "shadow":         "rgba(0,0,0,0.08)",
        "tooltip_bg":     "#37474F",
    },
    "dark": {
        "bg":             "#121212",
        "surface":        "#1E1E1E",
        "surface2":       "#2C2C2C",
        "border":         "#3A3A3A",
        "text":           "#E0E0E0",
        "text_secondary": "#9E9E9E",
        "accent":         "#90CAF9",
        "accent_hover":   "#64B5F6",
        "accent_light":   "#1A2A3A",
        "hover":          "#2A3A4A",
        "selected":       "#1E3A5F",
        "scrollbar_bg":   "#1E1E1E",
        "scrollbar_h":    "#555555",
        "tag_bg":         "#1565C0",
        "shadow":         "rgba(0,0,0,0.4)",
        "tooltip_bg":     "#263238",
    },
    "brown": {
        "bg":             "#2C1A10",
        "surface":        "#3E2314",
        "surface2":       "#4E2E1A",
        "border":         "#6B3E26",
        "text":           "#F5E6D3",
        "text_secondary": "#C4956A",
        "accent":         "#D4845A",
        "accent_hover":   "#E8956A",
        "accent_light":   "#3E2314",
        "hover":          "#5C3520",
        "selected":       "#7A4828",
        "scrollbar_bg":   "#3E2314",
        "scrollbar_h":    "#8B5A3A",
        "tag_bg":         "#D4845A",
        "shadow":         "rgba(0,0,0,0.4)",
        "tooltip_bg":     "#1C0E08",
    },
    "twilight": {
        "bg":             "#12111A",
        "surface":        "#1C1B28",
        "surface2":       "#252336",
        "border":         "#332F4D",
        "text":           "#E8E6F2",
        "text_secondary": "#9B96C0",
        "accent":         "#B388FF",
        "accent_hover":   "#9C64FF",
        "accent_light":   "#1E1A35",
        "hover":          "#2A2545",
        "selected":       "#3B3060",
        "scrollbar_bg":   "#1C1B28",
        "scrollbar_h":    "#5E4B8B",
        "tag_bg":         "#7C4DFF",
        "shadow":         "rgba(0,0,0,0.5)",
        "tooltip_bg":     "#1E1A35",
    },
    "ocean": {
        "bg":             "#0A1628",
        "surface":        "#0F2044",
        "surface2":       "#162A56",
        "border":         "#1E3A6E",
        "text":           "#C8E6FF",
        "text_secondary": "#7BAFD4",
        "accent":         "#00BCD4",
        "accent_hover":   "#00ACC1",
        "accent_light":   "#0F2044",
        "hover":          "#1A3060",
        "selected":       "#1E4080",
        "scrollbar_bg":   "#0F2044",
        "scrollbar_h":    "#1565C0",
        "tag_bg":         "#0097A7",
        "shadow":         "rgba(0,0,0,0.5)",
        "tooltip_bg":     "#05101E",
    },
    "forest": {
        "bg":             "#0D1F0F",
        "surface":        "#152B17",
        "surface2":       "#1C3820",
        "border":         "#2A5230",
        "text":           "#D4EDDA",
        "text_secondary": "#81C784",
        "accent":         "#4CAF50",
        "accent_hover":   "#43A047",
        "accent_light":   "#152B17",
        "hover":          "#1E3D22",
        "selected":       "#2E5C34",
        "scrollbar_bg":   "#152B17",
        "scrollbar_h":    "#388E3C",
        "tag_bg":         "#2E7D32",
        "shadow":         "rgba(0,0,0,0.4)",
        "tooltip_bg":     "#071209",
    },
    "sunset": {
        "bg":             "#1A0D00",
        "surface":        "#2C1500",
        "surface2":       "#3D1E00",
        "border":         "#6B3800",
        "text":           "#FFE8C8",
        "text_secondary": "#FFAB40",
        "accent":         "#FF6D00",
        "accent_hover":   "#E65100",
        "accent_light":   "#2C1500",
        "hover":          "#4A2200",
        "selected":       "#6B3200",
        "scrollbar_bg":   "#2C1500",
        "scrollbar_h":    "#BF360C",
        "tag_bg":         "#E64A19",
        "shadow":         "rgba(0,0,0,0.5)",
        "tooltip_bg":     "#0D0600",
    },
    "rose": {
        "bg":             "#1A0810",
        "surface":        "#2C1020",
        "surface2":       "#3D1530",
        "border":         "#6B2050",
        "text":           "#FFE4F0",
        "text_secondary": "#F48FB1",
        "accent":         "#E91E63",
        "accent_hover":   "#C2185B",
        "accent_light":   "#2C1020",
        "hover":          "#4A1030",
        "selected":       "#6B1545",
        "scrollbar_bg":   "#2C1020",
        "scrollbar_h":    "#880E4F",
        "tag_bg":         "#AD1457",
        "shadow":         "rgba(0,0,0,0.5)",
        "tooltip_bg":     "#0D0408",
    },
    "arctic": {
        "bg":             "#EBF3F8",
        "surface":        "#FFFFFF",
        "surface2":       "#F0F7FC",
        "border":         "#B8D4E8",
        "text":           "#1A2E3D",
        "text_secondary": "#4A7A9B",
        "accent":         "#0277BD",
        "accent_hover":   "#01579B",
        "accent_light":   "#E1F0FA",
        "hover":          "#D6EBFA",
        "selected":       "#B3D9F5",
        "scrollbar_bg":   "#D6EAF5",
        "scrollbar_h":    "#7BB8D8",
        "tag_bg":         "#0288D1",
        "shadow":         "rgba(2,119,189,0.10)",
        "tooltip_bg":     "#01304A",
    },
    "slate": {
        "bg":             "#1C2128",
        "surface":        "#252B36",
        "surface2":       "#2E3440",
        "border":         "#404854",
        "text":           "#CDD5DF",
        "text_secondary": "#8B97A8",
        "accent":         "#79C0FF",
        "accent_hover":   "#58A6FF",
        "accent_light":   "#252B36",
        "hover":          "#323A47",
        "selected":       "#3D4758",
        "scrollbar_bg":   "#252B36",
        "scrollbar_h":    "#546678",
        "tag_bg":         "#388BFD",
        "shadow":         "rgba(0,0,0,0.4)",
        "tooltip_bg":     "#10151C",
    },
    "midnight": {
        "bg":             "#01020A",
        "surface":        "#050C1A",
        "surface2":       "#091526",
        "border":         "#102240",
        "text":           "#B0C4DE",
        "text_secondary": "#5A7FA8",
        "accent":         "#4FC3F7",
        "accent_hover":   "#29B6F6",
        "accent_light":   "#050C1A",
        "hover":          "#0C1E38",
        "selected":       "#122B50",
        "scrollbar_bg":   "#050C1A",
        "scrollbar_h":    "#1A3A6A",
        "tag_bg":         "#0277BD",
        "shadow":         "rgba(0,0,0,0.7)",
        "tooltip_bg":     "#000308",
    },
    "sepia": {
        "bg":             "#F4ECD8",
        "surface":        "#FDF6E3",
        "surface2":       "#F9F0D8",
        "border":         "#D4B896",
        "text":           "#3D2B1F",
        "text_secondary": "#7A5C42",
        "accent":         "#8B5E3C",
        "accent_hover":   "#6D4830",
        "accent_light":   "#F4ECD8",
        "hover":          "#EAD9C0",
        "selected":       "#D9C4A0",
        "scrollbar_bg":   "#EAD9C0",
        "scrollbar_h":    "#B8956A",
        "tag_bg":         "#8B5E3C",
        "shadow":         "rgba(61,43,31,0.10)",
        "tooltip_bg":     "#2A1A0E",
    },
}

def _t(theme: str) -> dict:
    return THEMES.get(theme, THEMES["light"])


def _build_main_stylesheet(theme: str) -> str:
    t = _t(theme)
    return f"""
QMainWindow, QDialog, QWidget {{
    background-color: {t['bg']};
    color: {t['text']};
    font-family: 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
    font-size: 13px;
}}
QTreeWidget {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 10px;
    padding: 6px 4px;
    outline: none;
    selection-background-color: transparent;
}}
QTreeWidget::item {{
    padding: 5px 8px;
    min-height: 24px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QTreeWidget::item:hover {{
    background-color: {t['hover']};
}}
QTreeWidget::item:selected {{
    background-color: {t['selected']};
    color: {t['text']};
    font-weight: 600;
}}
QTreeWidget::branch {{ background: transparent; }}
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1.5px solid {t['border']};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {t['accent']};
    selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {t['accent']};
    background-color: {t['surface2']};
}}
QLineEdit#SearchBar {{
    background-color: {t['surface2']};
    border: 1.5px solid {t['border']};
    border-radius: 20px;
    padding: 7px 14px;
    font-size: 13px;
}}
QLineEdit#SearchBar:focus {{ border-color: {t['accent']}; }}
QPushButton {{
    background-color: {t['surface2']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {t['hover']};
    border-color: {t['accent']};
}}
QPushButton:pressed {{ background-color: {t['selected']}; }}
QPushButton:disabled {{
    color: {t['text_secondary']};
    background-color: {t['surface']};
    border-color: {t['border']};
}}
QComboBox {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1.5px solid {t['border']};
    border-radius: 8px;
    padding: 5px 10px;
    min-width: 80px;
}}
QComboBox:hover {{ border-color: {t['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    selection-background-color: {t['hover']};
    selection-color: {t['text']};
    padding: 4px;
}}
QLabel {{
    color: {t['text']};
    background-color: transparent;
}}
QSplitter::handle {{
    background-color: {t['border']};
    width: 1px;
    height: 1px;
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{ background-color: transparent; }}
QGroupBox {{
    border: 1px solid {t['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
    color: {t['text_secondary']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    background-color: {t['bg']};
}}
QTabWidget::pane {{
    border: 1px solid {t['border']};
    border-radius: 10px;
    background-color: {t['surface']};
}}
QTabBar::tab {{
    background-color: {t['surface2']};
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 6px 16px;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {t['surface']};
    color: {t['accent']};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{ background-color: {t['hover']}; }}
QToolTip {{
    background-color: {t['tooltip_bg']};
    color: #FFFFFF;
    border: none;
    padding: 5px 10px;
    font-size: 11px;
    border-radius: 6px;
}}
#PreviewContent {{
    background-color: transparent;
    border: 2px solid {t['accent']};
    border-radius: 12px;
    padding: 8px;
}}
#PreviewContainer {{
    border: 2px solid {t['accent']};
    border-radius: 12px;
    background-color: {t['surface']};
    padding: 8px;
}}
"""

LIGHT_THEME_STYLESHEET    = _build_main_stylesheet("light")
DARK_THEME_STYLESHEET     = _build_main_stylesheet("dark")
BROWN_THEME_STYLESHEET    = _build_main_stylesheet("brown")
TWILIGHT_THEME_STYLESHEET = _build_main_stylesheet("twilight")


def get_full_stylesheet(theme: str) -> str:
    return _build_main_stylesheet(theme)


def apply_common_styles(window):
    for btn in [
        window.reindex_button, window.import_button, window.reset_button,
        window.info_button, window.theme_button, window.search_button,
        window.zoom_in_button, window.zoom_out_button,
        window.prev_page_button, window.next_page_button,
        window.meta_tag_add_button,
    ]:
        btn.setStyleSheet(get_uniform_button_style(window.current_theme))
        btn.setFixedSize(40, 40)
    window.tree.setStyleSheet(_build_main_stylesheet(window.current_theme))
    window.metadata_form.setStyleSheet(get_metadata_form_style(window.current_theme))
    scrollbar_style = get_scrollbar_style(window.current_theme)
    app = QApplication.instance()
    app.setStyleSheet(_build_main_stylesheet(window.current_theme) + scrollbar_style)


def get_uniform_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton {{
        background-color: transparent;
        border: none;
        border-radius: 20px;
        padding: 6px;
    }}
    QPushButton:hover {{ background-color: {t['hover']}; }}
    QPushButton:pressed {{ background-color: {t['selected']}; }}
    QToolTip {{
        background-color: {t['tooltip_bg']};
        color: #FFFFFF;
        border: none;
        padding: 5px 10px;
        font-size: 11px;
        border-radius: 6px;
    }}
    """

def get_save_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton {{
        font-size: 13px; padding: 8px 20px;
        background-color: {t['accent']}; color: white;
        border: none; border-radius: 20px;
        font-weight: 600; letter-spacing: 0.3px;
    }}
    QPushButton:hover {{ background-color: {t['accent_hover']}; }}
    """

def get_tag_add_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton#tagAddButton {{
        background-color: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; font-size: 12px;
        border-radius: 12px; padding: 4px 10px; font-weight: 500;
    }}
    QPushButton#tagAddButton:hover {{
        background-color: {t['accent']}; color: white; border-color: {t['accent']};
    }}
    """

def get_save_confirmation_label_style(theme: str = "light") -> str:
    return "QLabel { color: #4CAF50; font-size: 11px; padding: 4px; font-weight: 500; }"

def get_light_button_style() -> str:
    t = _t("light")
    return f"""
    QPushButton {{
        border: 1.5px solid {t['border']}; border-radius: 8px;
        background-color: {t['surface']}; color: {t['text']};
        padding: 6px 12px; font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {t['hover']}; border-color: {t['accent']}; }}
    """

def get_dark_button_style() -> str:
    t = _t("dark")
    return f"""
    QPushButton {{
        border: 1.5px solid {t['border']}; border-radius: 8px;
        background-color: {t['surface2']}; color: {t['text']};
        padding: 6px 12px; font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {t['hover']}; border-color: {t['accent']}; }}
    """

def get_theme_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton {{
        border: 1.5px solid {t['border']}; border-radius: 8px;
        background-color: {t['surface2']}; color: {t['text']};
        padding: 6px 12px; font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {t['hover']}; border-color: {t['accent']}; }}
    """

def get_icon_button_style_light() -> str:
    return get_uniform_button_style("light")

def get_icon_button_style_dark() -> str:
    return get_uniform_button_style("dark")

def get_bottom_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton {{ background-color: transparent; border: none; border-radius: 20px; }}
    QPushButton:hover {{ background-color: {t['hover']}; }}
    QPushButton:pressed {{ background-color: {t['selected']}; }}
    """

def get_zoom_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton#ZoomInButton, QPushButton#ZoomOutButton,
    QPushButton#PrevPageButton, QPushButton#NextPageButton {{
        color: {t['accent']}; font-weight: bold;
        background-color: transparent; border: none;
        font-size: 16px; border-radius: 6px;
    }}
    QPushButton#ZoomInButton:hover, QPushButton#ZoomOutButton:hover,
    QPushButton#PrevPageButton:hover, QPushButton#NextPageButton:hover {{
        background-color: {t['accent_light']}; border-radius: 6px;
    }}
    """

def get_text_preview_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QTextEdit {{
        background-color: {t['surface']}; color: {t['text']};
        font-size: 13px; padding: 14px;
        border: none; border-radius: 10px;
    }}
    """

def get_metadata_toggle_button_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QPushButton {{
        background-color: transparent; color: {t['accent']};
        border: none; font-weight: 600; font-size: 12px;
        padding: 4px 8px; border-radius: 6px;
    }}
    QPushButton:hover {{ background-color: {t['accent_light']}; }}
    """

def get_metadata_form_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QLineEdit, QTextEdit {{
        background-color: {t['surface']}; color: {t['text']};
        border: 1.5px solid {t['border']}; padding: 5px 8px;
        font-size: 12px; border-radius: 8px;
    }}
    QLineEdit:focus, QTextEdit:focus {{ border-color: {t['accent']}; }}
    QLabel {{
        font-size: 11px; font-weight: 600;
        color: {t['text_secondary']}; letter-spacing: 0.3px;
    }}
    """

def get_message_box_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QMessageBox {{
        background-color: {t['surface']}; color: {t['text']};
        font-size: 13px; border-radius: 10px;
    }}
    QMessageBox QPushButton {{
        background-color: {t['accent']}; color: white;
        border: none; border-radius: 8px;
        padding: 6px 18px; font-weight: 600; min-width: 80px;
    }}
    QMessageBox QPushButton:hover {{ background-color: {t['accent_hover']}; }}
    """

def get_tag_input_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QComboBox {{
        background-color: {t['surface']}; color: {t['text']};
        border: 1.5px solid {t['border']}; border-radius: 14px;
        padding: 5px 12px; font-size: 12px; font-weight: 500;
    }}
    QComboBox:hover {{ border-color: {t['accent']}; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding; subcontrol-position: top right;
        width: 22px; border-left: 1px solid {t['border']};
        background-color: transparent;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['surface']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 8px;
        selection-background-color: {t['hover']};
        selection-color: {t['text']}; padding: 4px;
    }}
    """

def get_tag_widget_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QFrame {{
        background-color: {t['tag_bg']}; border-radius: 12px;
        padding: 2px 8px; margin: 3px;
    }}
    QLabel {{
        color: white; font-size: 11px; font-weight: 600;
        padding-left: 2px; padding-right: 4px; background: transparent;
    }}
    QPushButton#tagRemoveButton {{
        background-color: transparent; color: rgba(255,255,255,0.7);
        font-weight: bold; font-size: 13px;
        border: none; padding-left: 4px;
    }}
    QPushButton#tagRemoveButton:hover {{ color: #FF5252; }}
    """

def get_round_button_style(theme: str = "light") -> str:
    return get_uniform_button_style(theme)

def get_language_button_style() -> str:
    return """
    QPushButton {
        background-color: transparent; border: none;
        border-radius: 20px; width: 40px; height: 40px; padding: 0;
    }
    QPushButton:hover { background-color: rgba(128,128,128,0.15); }
    """

def get_scrollbar_style(theme: str = "light") -> str:
    t = _t(theme)
    return f"""
    QScrollBar:vertical {{
        border: none; background: {t['scrollbar_bg']};
        width: 8px; border-radius: 4px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scrollbar_h']}; min-height: 30px; border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QScrollBar:horizontal {{
        border: none; background: {t['scrollbar_bg']};
        height: 8px; border-radius: 4px; margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['scrollbar_h']}; min-width: 30px; border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t['accent']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """

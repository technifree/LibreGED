# LibreGED v2.9.1 - 17/05/2026

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QSplitter, QSplitterHandle, QScrollArea,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QMessageBox, QMenu, QToolTip, QSizePolicy, QSpacerItem, QStackedLayout,
    QGraphicsOpacityEffect, QApplication, QStyleFactory, QDialog, QStackedWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QFileDialog,
    QProgressBar, QInputDialog, QComboBox, QToolButton
)

from PySide6.QtCore import (
    Qt, QTimer, QEvent, QUrl, QThread, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QSize, QObject, Signal, QMimeData, QPoint,
    Property
)

from PySide6.QtGui import (
    QPixmap, QImage, QIcon, QTransform, QAction, QPalette, QColor, QFont,
    QTextOption, QDesktopServices, QGuiApplication, QDrag,
    QKeySequence, QTextCursor, QTextCharFormat, QShortcut
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except Exception:
    WEB_ENGINE_AVAILABLE = False
    QWebEngineView = None

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# Importation des modules externes
import os
import sys
import subprocess
import qtawesome as qta
import fitz # PyMuPDF
import config
import pandas as pd
from PIL import Image, ExifTags
from PIL.ImageQt import ImageQt
from database import odf_utils
from database.db import fetch_all_documents, save_metadata_to_db, search_documents, matches_content, get_metadata_for_path, get_all_tags
from database.reindex import scan_and_insert_files, reindex_files_with_progress
from database.odf_utils import odt_to_html, ods_to_html, odp_to_html
from database.path_utils import win_path, path_exists, path_is_file, path_is_dir, path_is_symlink, open_folder_in_explorer
from ebooklib import epub
from bs4 import BeautifulSoup
from datetime import datetime
from collections import Counter
import json
#from config import FILES_DIR, DB_PATH, ASSETS_DIR, LOGO_PATH, LANGUAGES_PATH, load_user_language, save_user_language, load_user_theme, save_user_theme
from pathlib import Path
from docx import Document
import mammoth
from odf.opendocument import load
from odf.text import P, H, Span
import sqlite3
import shutil
from shutil import copy2
import humanize
import platform
import ctypes
import random

def _is_symlink_robust(path) -> bool:
    """Détecte symlinks ET jonctions NTFS Windows via os.path.islink."""
    try:
        return os.path.islink(str(path))
    except (OSError, ValueError):
        return False


def _safe_rel(abs_path, base) -> str | None:
    """Chemin relatif robuste Windows/Linux. Retourne None si impossible."""
    try:
        return str(Path(str(abs_path)).relative_to(Path(str(base))))
    except ValueError:
        pass
    try:
        return os.path.relpath(str(abs_path), str(base))
    except (ValueError, OSError):
        return None


from views.folder_browser import FolderBrowserWidget

TAG_COLORS = [
    "#007BFF", "#28a745", "#17a2b8", "#e67e22",
    "#6f42c1", "#fd7e14", "#20c997", "#e83e8c",
]

def tag_color(tag: str) -> str:
    """
    Retourne une couleur déterministe pour un tag donné.
    Utilise sum(ord) au lieu de hash() — stable entre sessions
    (hash() dépend de PYTHONHASHSEED qui change à chaque lancement).
    """
    stable_key = sum(ord(c) for c in tag)
    return TAG_COLORS[stable_key % len(TAG_COLORS)]

def has_symlink_privileges():
    """Vérifie si l'utilisateur a les droits pour créer un lien symbolique (utile sous Windows)."""
    if os.name != 'nt':
        return True  # Sous Linux/macOS, pas besoin de privilèges spéciaux

    # Sous Windows, il faut généralement des privilèges administrateur
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

# Gestion des WebEngine si disponible
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    QWebEngineView = None

# Importation des styles
from styles import (
    LIGHT_THEME_STYLESHEET,
    DARK_THEME_STYLESHEET,
    BROWN_THEME_STYLESHEET,
    TWILIGHT_THEME_STYLESHEET,
    THEMES,
    apply_common_styles,
    get_uniform_button_style,
    get_save_button_style,
    get_tag_add_button_style,
    get_save_confirmation_label_style,
    get_icon_button_style_light,
    get_icon_button_style_dark,
    get_zoom_button_style,
    get_text_preview_style,
    get_metadata_toggle_button_style,
    get_metadata_form_style,
    get_bottom_button_style,
    get_message_box_style,
    get_round_button_style,
    get_language_button_style,
    get_dark_button_style,
    get_light_button_style,
    get_theme_button_style,
    get_tag_widget_style,
    get_tag_input_style,
    get_full_stylesheet,
    get_scrollbar_style,
)


def get_flag_icon(lang_code):
    flag_path = config.ASSETS_DIR / "flags" / f"{lang_code}.png"
    return QIcon(str(flag_path)) if flag_path.exists() else QIcon()


def resource_path(relative_path):
    """Retourne le chemin des ressources après compilation."""
    try:
        if getattr(sys, 'frozen', False):
            # Si l'application est exécutée depuis PyInstaller
            base_path = sys._MEIPASS
        else:
            # Sinon, utilise le répertoire courant
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        print(f"[ERREUR] chemin des ressources: {e}")
        return relative_path

def matches_content(file_path, query, translate):
    import logging
    logger = logging.getLogger("libreged")

    ext = os.path.splitext(file_path)[1].lower()
    query = query.lower()

    try:
        if ext in [".txt", ".md", ".html", ".htm", ".py"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return query in f.read().lower()

        elif ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                for page in doc:
                    if query in page.get_text().lower():
                        return True
            except Exception as e:
                print(f"[MuPDF] Erreur sur {file_path}: {e}")

        elif ext in [".doc", ".docx"]:
            try:
                import mammoth
                with open(file_path, "rb") as docx_file:
                    result = mammoth.convert_to_html(docx_file)
                    return query in result.value.lower()
            except Exception:
                try:
                    from docx import Document
                    from docx.opc.exceptions import PackageNotFoundError
                    doc = Document(file_path)
                    return any(query in p.text.lower() for p in doc.paragraphs)
                except PackageNotFoundError:
                    # Fichier non lisible / faux document Word
                    return False
                except Exception:
                    return False

        elif ext == ".epub":
            try:
                from ebooklib import epub
                from bs4 import BeautifulSoup
                book = epub.read_epub(str(file_path))
                for item in book.get_items():
                    if item.get_type() == 9:  # DOCUMENT
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        if query in soup.get_text().lower():
                            return True
            except Exception:
                return False

        elif ext in [".odt", ".odf"]:
            try:
                content = odf_utils.extract_text_from_odt(file_path)
                return query in content.lower()
            except Exception:
                return False

        elif ext == ".ods":
            try:
                content = odf_utils.ods_to_html(file_path)
                return query in content.lower()
            except Exception:
                return False

        elif ext == ".odp":
            try:
                content = odf_utils.odp_to_html(file_path)
                return query in content.lower()
            except Exception:
                return False

        elif ext == ".xlsx":
            try:
                content = odf_utils.extract_text_from_xlsx(file_path)
                return query in content.lower()
            except Exception:
                return False

        elif ext == ".pptx":
            try:
                content = odf_utils.extract_text_from_pptx(file_path)
                return query in content.lower()
            except Exception:
                return False

        elif ext in (".mhtml", ".mht"):
            try:
                # MHTML est un format texte — extraction brute du contenu
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw, "html.parser")
                return query in soup.get_text().lower()
            except Exception:
                return False

        elif ext == ".eml":
            try:
                import email as email_lib
                from email import policy
                with open(file_path, "rb") as f:
                    msg = email_lib.message_from_binary_file(f, policy=policy.default)
                # Chercher dans les en-têtes
                headers = " ".join([
                    str(msg.get("Subject", "")),
                    str(msg.get("From", "")),
                    str(msg.get("To", "")),
                ]).lower()
                if query in headers:
                    return True
                # Chercher dans le corps
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        if ct in ("text/plain", "text/html"):
                            try:
                                text = part.get_content().lower()
                                if query in text:
                                    return True
                            except Exception:
                                pass
                else:
                    try:
                        text = msg.get_content().lower()
                        if query in text:
                            return True
                    except Exception:
                        pass
            except Exception:
                return False

    except Exception :
        # log optionnel : commenter ou activer si besoin de traces silencieuses
        # logger.debug(f"[IGNORE] Lecture impossible pour {file_path}: {e}")
        # ou commenter complètement cette ligne si silence total
        pass 

    return False

import sqlite3
import os
import config

def matches_metadata(doc_path, keywords):
    # 1. Normalisation du chemin
    doc_path = os.path.normpath(str(doc_path))
    # 2. Normalisation des keywords
    keywords = [kw.strip().lower() for kw in keywords]

    try:
        with sqlite3.connect(config.DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tags, comment FROM document_metadata WHERE document_path = ?",
                (doc_path,)
            )
            row = cur.fetchone()
            if not row:
                return False

            tags, comment = row
            content = f"{tags or ''} {comment or ''}".lower()
            # 3. Recherche case-insensitive
            return any(kw in content for kw in keywords)

    except Exception as e:
        print(f"[ERREUR] Recherche metadata : {e}")
        return False


def get_qta_icon_for_extension(ext):
    ext = ext.lower()
    if ext in ['.pdf']:
        return qta.icon("fa5.file-pdf")
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff']:
        return qta.icon("fa5.file-image")
    elif ext in ['.txt', '.md']:
        return qta.icon("fa5.file-alt")
    elif ext in ['.html', '.htm']:
        return qta.icon("fa5.file-code")
    else:
        return qta.icon("fa5.file")

def get_icon_for_extension(ext, theme="dark", color="#0078D7"):
    import qtawesome as qta
    icon_map = {
        '.pdf': 'fa5s.file-pdf',
        '.txt': 'fa5s.file-alt',
        '.md': 'fa5s.file-alt',
        '.html': 'fa5s.file-code',
        '.jpg': 'fa5s.file-image',
        '.jpeg': 'fa5s.file-image',
        '.png': 'fa5s.file-image',
        '.gif': 'fa5s.file-image',
        '.bmp': 'fa5s.file-image',
        '.tif': 'fa5s.file-image',
        '.tiff': 'fa5s.file-image',
        '.epub': 'fa5s.book'
    }

    icon_name = icon_map.get(ext.lower(), 'fa5s.file')
    return qta.icon(icon_name, color=color)

def get_folder_icon(color="#0078D7"):
    import qtawesome as qta
    return qta.icon("fa5s.folder", color=color)


def extract_all_text_from_docx(path, translate):
    try:
        from docx import Document
        doc = Document(path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text).strip()
    except Exception as e:
        print(f"[ERROR] {translate('docx_read_error')}: {e}")
        return None


def convert_docx_to_html(path):
    with open(path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value  
        messages = result.messages  
    return html

# ──────────────────────────────────────────────────────────────────────────────
# Splitter avec bouton accordéon sur la poignée
# ──────────────────────────────────────────────────────────────────────────────

class DraggableTreeWidget(QTreeWidget):
    """
    QTreeWidget avec drag and drop interne pour reorganiser fichiers/dossiers.
    - Glisser un item vers un dossier cible = deplacement sur disque + reindexation
    - Drop sur la zone vide = deplacement a la racine de FILES_DIR
    - Signal item_moved(src_rel, dst_rel) emis apres chaque deplacement
    - Accepte aussi les drops externes depuis l'explorateur (Copier / Déplacer)
    """

    item_moved    = Signal(str, str)
    external_drop = Signal(list, str, str)  # (paths, dest_rel, mode:"copy"|"move")
    _DRAG_THRESHOLD = 6

    def __init__(self, files_dir, parent=None):
        super().__init__(parent)
        self._files_dir = files_dir
        self._drag_start_pos  = None
        self._drag_start_item = None
        self._drop_target_item = None
        self.setAcceptDrops(True)
        self.setDragEnabled(False)

    def _install_drag_filter(self):
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            t = event.type()
            if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                item = self.itemAt(event.pos())
                rel  = item.data(0, Qt.ItemDataRole.UserRole) if item else None
                if rel:
                    self._drag_start_pos  = QPoint(event.pos())
                    self._drag_start_item = item
                else:
                    self._drag_start_pos  = None
                    self._drag_start_item = None
            elif t == QEvent.MouseMove and self._drag_start_pos is not None:
                if (event.pos() - self._drag_start_pos).manhattanLength() >= self._DRAG_THRESHOLD:
                    self._start_internal_drag()
                    self._drag_start_pos  = None
                    self._drag_start_item = None
                    return True
            elif t == QEvent.MouseButtonRelease:
                self._drag_start_pos  = None
                self._drag_start_item = None
        return super().eventFilter(obj, event)

    def _start_internal_drag(self):
        items = self.selectedItems()
        if self._drag_start_item and self._drag_start_item not in items:
            items = [self._drag_start_item]
        rel_paths = []
        for item in items:
            rel = item.data(0, Qt.ItemDataRole.UserRole)
            if rel:
                rel_paths.append(rel)
        if not rel_paths:
            return
        mime = QMimeData()
        mime.setData('application/x-libreged-paths',
                     '\n'.join(rel_paths).encode('utf-8'))
        urls = [QUrl.fromLocalFile(str(self._files_dir / r)) for r in rel_paths]
        mime.setUrls(urls)
        sep = bytes([13, 10])
        mime.setData('text/uri-list',
                     sep.join(u.toString().encode('utf-8') for u in urls) + sep)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-libreged-paths'):
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            # Drop externe depuis l'explorateur de fichiers
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        has_internal = event.mimeData().hasFormat('application/x-libreged-paths')
        has_external = event.mimeData().hasUrls()
        if not (has_internal or has_external):
            event.ignore()
            return
        target_item = self.itemAt(event.pos())
        if target_item is None:
            self._highlight_drop_target(None)
            event.acceptProposedAction()
        else:
            item_type = target_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == 'folder':
                self._highlight_drop_target(target_item)
                event.acceptProposedAction()
            else:
                parent = target_item.parent()
                self._highlight_drop_target(parent)
                event.acceptProposedAction()

    def dropEvent(self, event):
        self._highlight_drop_target(None)
        mime = event.mimeData()

        # --- Résoudre la destination ---
        target_item = self.itemAt(event.pos())
        if target_item is None:
            dest_rel = ''
        else:
            item_type = target_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == 'folder':
                dest_rel = target_item.data(0, Qt.ItemDataRole.UserRole)
            else:
                parent = target_item.parent()
                dest_rel = parent.data(0, Qt.ItemDataRole.UserRole) if parent else ''

        # --- Drop INTERNE (réorganisation) ---
        if mime.hasFormat('application/x-libreged-paths'):
            raw = mime.data('application/x-libreged-paths').data()
            src_rels = raw.decode('utf-8').strip().splitlines()
            import shutil
            errors = []
            moved  = []
            for src_rel in src_rels:
                src_path = self._files_dir / src_rel
                dest_dir = self._files_dir / dest_rel if dest_rel else self._files_dir
                try:
                    dest_dir.resolve().relative_to(src_path.resolve())
                    continue
                except ValueError:
                    pass
                if src_path.parent.resolve() == dest_dir.resolve():
                    continue
                dest_path = dest_dir / src_path.name
                if dest_path.exists():
                    errors.append(src_path.name + ' : existe deja dans la destination')
                    continue
                try:
                    shutil.move(str(src_path), str(dest_path))
                    moved.append((src_rel, str(dest_path.relative_to(self._files_dir))))
                except Exception as e:
                    errors.append(src_path.name + ' : ' + str(e))
            if moved:
                for src_rel, new_rel in moved:
                    self.item_moved.emit(src_rel, new_rel)
            if errors:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, 'Erreur de deplacement',
                    'Certains elements ne peuvent pas etre deplaces :\n' + '\n'.join(errors))
            event.acceptProposedAction()
            return

        # --- Drop EXTERNE (depuis l'explorateur) ---
        if mime.hasUrls():
            ext_paths = []
            for url in mime.urls():
                local = url.toLocalFile()
                if local and local not in (str(self._files_dir / dest_rel),):
                    # Exclure les fichiers déjà dans files_dir
                    from pathlib import Path as _Path
                    p = _Path(local)
                    try:
                        p.relative_to(self._files_dir)
                        continue   # déjà dedans → drop interne géré autrement
                    except ValueError:
                        pass
                    ext_paths.append(local)

            if ext_paths:
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
                dlg = QDialog(self)
                dlg.setWindowTitle("Importer des fichiers")
                lv = QVBoxLayout(dlg)
                lv.addWidget(QLabel("Choisissez l'action :"))
                combo = QComboBox()
                combo.addItems(["Copier", "Déplacer"])
                lv.addWidget(combo)
                row = QHBoxLayout()
                row.addStretch()
                from PySide6.QtWidgets import QPushButton as _QB
                b_cancel = _QB("Annuler"); b_cancel.clicked.connect(dlg.reject)
                b_ok = _QB("OK"); b_ok.clicked.connect(dlg.accept); b_ok.setDefault(True)
                row.addWidget(b_cancel); row.addWidget(b_ok)
                lv.addLayout(row)
                if dlg.exec() == QDialog.Accepted:
                    mode = "move" if combo.currentText() == "Déplacer" else "copy"
                    self.external_drop.emit(ext_paths, dest_rel, mode)
            event.acceptProposedAction()

    def _highlight_drop_target(self, item):
        if self._drop_target_item and self._drop_target_item is not item:
            self._drop_target_item.setBackground(0, self.palette().base())
        self._drop_target_item = item
        if item:
            from PySide6.QtGui import QColor
            item.setBackground(0, QColor('#1e4d99'))

class DoubleClickLabel(QLabel):
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


def _file_dialog_options():
    """
    Sur Linux compilé avec PyInstaller, le dialog GTK natif charge
    des plugins incompatibles avec les libs bundlées (LD_LIBRARY_PATH).
    On force le dialog Qt natif pour éviter les crashes silencieux.
    """
    import sys
    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        return QFileDialog.Option.DontUseNativeDialog
    return QFileDialog.Option(0)  # aucune option


class ThemePickerDialog(QDialog):
    """Modale de sélection du thème avec aperçu visuel."""

    THEME_META = {
        "light":    {"label_key": "theme_light",    "icon_color": "#1976D2"},
        "dark":     {"label_key": "theme_dark",     "icon_color": "#90CAF9"},
        "brown":    {"label_key": "theme_brown",    "icon_color": "#D4845A"},
        "twilight": {"label_key": "theme_twilight", "icon_color": "#B388FF"},
        "ocean":    {"label_key": "theme_ocean",    "icon_color": "#00BCD4"},
        "forest":   {"label_key": "theme_forest",   "icon_color": "#4CAF50"},
        "sunset":   {"label_key": "theme_sunset",   "icon_color": "#FF6D00"},
        "rose":     {"label_key": "theme_rose",     "icon_color": "#E91E63"},
        "arctic":   {"label_key": "theme_arctic",   "icon_color": "#0277BD"},
        "slate":    {"label_key": "theme_slate",    "icon_color": "#79C0FF"},
        "midnight": {"label_key": "theme_midnight", "icon_color": "#4FC3F7"},
        "sepia":    {"label_key": "theme_sepia",    "icon_color": "#8B5E3C"},
    }

    def __init__(self, current_theme: str, translate_fn, parent=None):
        super().__init__(parent)
        self.selected_theme = current_theme
        self.t = translate_fn
        self.setWindowTitle(self.t("theme_picker_title"))
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._build_ui(current_theme)

    def _build_ui(self, current_theme: str):
        from styles import THEMES
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        t = THEMES.get(current_theme, THEMES["light"])

        card = QWidget()
        card.setObjectName("ThemeCard")
        card.setStyleSheet(f"""
            QWidget#ThemeCard {{
                background-color: {t['surface']};
                border-radius: 16px;
                border: 1px solid {t['border']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        title = QLabel(self.t("theme_picker_title"))
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {t['text']}; background: transparent;")
        card_layout.addWidget(title)

        subtitle = QLabel(self.t("theme_picker_subtitle"))
        subtitle.setStyleSheet(f"font-size: 12px; color: {t['text_secondary']}; background: transparent;")
        card_layout.addWidget(subtitle)

        grid = QWidget()
        grid.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(10)

        items = list(self.THEME_META.items())
        for idx, (theme_key, meta) in enumerate(items):
            row, col = divmod(idx, 4)
            btn = self._make_theme_button(theme_key, meta, THEMES[theme_key], current_theme)
            grid_layout.addWidget(btn, row, col)

        card_layout.addWidget(grid)

        close_btn = QPushButton(self.t("theme_picker_close"))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['surface2']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 7px 20px;
                font-weight: 500;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t['hover']};
                color: {t['text']};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        card_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        outer.addWidget(card)

    def _make_theme_button(self, theme_key, meta, palette, current_theme):
        is_active = (theme_key == current_theme)
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(160, 80)
        accent_border = ("3px solid " + palette["accent"]) if is_active else ("1px solid " + palette["border"])
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {palette['surface']};
                border: {accent_border};
                border-radius: 12px;
                text-align: left;
                padding: 10px 14px;
            }}
            QPushButton:hover {{ border: 2px solid {palette['accent']}; }}
        """)
        btn_layout = QVBoxLayout(btn)
        btn_layout.setContentsMargins(10, 8, 10, 8)
        btn_layout.setSpacing(4)

        swatch_row = QWidget()
        swatch_row.setStyleSheet("background: transparent;")
        swatch_layout = QHBoxLayout(swatch_row)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setSpacing(4)
        for color in [palette["bg"], palette["accent"], palette["surface2"]]:
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            swatch_layout.addWidget(dot)
        swatch_layout.addStretch()
        btn_layout.addWidget(swatch_row)

        checkmark = "✓  " if is_active else ""
        lbl = QLabel(f"{checkmark}{self.t(meta['label_key'])}")
        lbl.setStyleSheet(f"color: {palette['text']}; font-weight: {'700' if is_active else '500'}; font-size: 12px; background: transparent;")
        btn_layout.addWidget(lbl)

        btn.clicked.connect(lambda checked=False, k=theme_key: self._select(k))
        return btn

    def _select(self, theme_key: str):
        self.selected_theme = theme_key
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreGED")
        # Récupère la taille disponible de l'écran
        screen = QGuiApplication.primaryScreen()
        geom = screen.availableGeometry()
        # Définir une taille par défaut à 90 % de la largeur/hauteur
        default_width  = min(int(geom.width()  * 0.9), 1000)
        default_height = min(int(geom.height() * 0.9),  900)
        # Redimensionne la fenêtre à cette taille par défaut
        self.resize(default_width, default_height)
        self.setMinimumSize(600, 400)

        # Restaurer la géométrie de la fenêtre depuis config.json
        saved_cfg = config.load_config()
        saved_geom = saved_cfg.get("window_geometry")
        if saved_geom:
            try:
                from PySide6.QtCore import QRect
                g = saved_geom
                self.setGeometry(g[0], g[1], g[2], g[3])
            except Exception:
                pass

        # --- Initialisation du compteur de résultats de recherche ---
        self.search_result_count = 0
        self.search_count_label = QLabel("")
        self.search_count_label.hide()
        self.statusBar().addPermanentWidget(self.search_count_label)

        self.current_theme = config.load_user_theme()
        self.current_language = config.load_user_language()
        self.load_translations()

        self.t = lambda key: self.translations.get(self.current_language, {}).get(key, key)

        self.file_info_label = DoubleClickLabel("")
        self.file_info_label.setToolTip(self.t("tooltip_open_with_default_app") if hasattr(self, "translations") else "")
        self.file_info_label.doubleClicked.connect(self.open_current_file_with_default_app)
        self.file_info_label.setCursor(Qt.PointingHandCursor)
        self.file_info_label.setStyleSheet("padding-left: 10px; font-style: italic; text-decoration: underline;")
        self.statusBar().addWidget(self.file_info_label)  

        #affichage du nombre de fichiers trouvés lors de la recheche
        self.search_count_label = QLabel("")  
        self.search_count_label.setStyleSheet("padding-right: 10px; font-weight: bold; color: #3366cc;")
        self.statusBar().addPermanentWidget(self.search_count_label)
        
        self.update_window_title()

        # Définir le style des boutons
        self.button_style = get_theme_button_style(self.current_theme)

        # -- Panneau gauche --
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setStyleSheet("background-color: transparent; border-radius: 12px;")

        
        # --- Logo ---
        self.logo_label = QLabel()
        # à ce stade, self.current_theme DOIT être défini
        logo_path = config.get_logo_path(self.current_theme)
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaledToWidth(160, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled)
            else:
                print("[ERREUR] Pixmap vide malgré le chemin")
                self.logo_label.setText("Logo attention")
        else:
            print("[ERREUR] Le fichier logo est introuvable")
            self.logo_label.setText("logo KO")

        self.logo_label.setStyleSheet("background: transparent;")
        self.logo_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.logo_label)

        left_layout.addSpacing(10)

        # --- Nombre de fichiers ---
        self.file_count_label = QLabel()
        self.file_count_label.setAlignment(Qt.AlignCenter)
        self.file_count_label.setStyleSheet("font-weight: bold; color: #3366cc;")
        left_layout.addWidget(self.file_count_label)

        left_layout.addSpacing(10)

        # --- Zone de recherche ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_input.returnPressed.connect(self.perform_search)

        self.search_button = QPushButton()
        self.search_button.setIcon(qta.icon("fa5s.search", color="#007BFF"))
        self.search_button.setToolTip(self.t("search_tooltip"))
        self.search_button.clicked.connect(self.perform_search)

        self.tag_filter_button = QPushButton()
        self.tag_filter_button.setIcon(qta.icon("fa5s.tags", color="#248afd"))
        self.tag_filter_button.setToolTip(self.t("filter_by_tag"))
        self.tag_filter_button.clicked.connect(self.toggle_tag_filter)

        # Appliquer le même style que les autres 
        icon_button_style = (
            get_icon_button_style_dark()
            if self.current_theme == "dark"
            else get_icon_button_style_light()
        )
        self.tag_filter_button.setStyleSheet(icon_button_style)
        self.tag_filter_button.setFixedSize(40, 40)

        search_layout.addWidget(self.tag_filter_button)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        left_layout.addLayout(search_layout)

        # Bouton pour arrêter / réinitialiser la recherche
        self.stop_search_button = QPushButton()
        self.stop_search_button.setIcon(qta.icon("fa5s.stop-circle", color="red"))
        self.stop_search_button.setToolTip(self.t("stop_search"))

        # Flag pour savoir si une recherche est en cours
        self._is_searching = False

        # " Bouton 'Arrêter' (pour stopper la recherche en cours) "
        self.stop_search_button.clicked.connect(self.stop_search)
        self.stop_search_button.setVisible(False)
        search_layout.addWidget(self.stop_search_button)

        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setVisible(False)
        self.tag_filter_combo.setStyleSheet(get_tag_input_style(self.current_theme))
        self.tag_filter_combo.setPlaceholderText(self.t("select_tag_filter"))

        # Connexion du filtre par tag : on reÃ§oit l'index, puis on appelle filter_by_selected_tag
        self.tag_filter_combo.currentIndexChanged.connect(
            lambda idx: self.filter_by_selected_tag(self.tag_filter_combo.itemText(idx))
        )
        

        left_layout.addWidget(self.tag_filter_combo)

        self.tag_filter_arrow = QToolButton(self.tag_filter_combo)
        self.tag_filter_arrow.setIcon(qta.icon("fa5s.chevron-down", color="white" if self.current_theme == "dark" else "black"))
        self.tag_filter_arrow.setCursor(Qt.PointingHandCursor)
        self.tag_filter_arrow.setStyleSheet("border: none;")
        self.tag_filter_arrow.setFixedSize(18, 18)
        self.tag_filter_arrow.setFocusPolicy(Qt.NoFocus)
        self.tag_filter_arrow.clicked.connect(self.tag_filter_combo.showPopup)

        # Positionner dynamiquement
        self.tag_filter_combo.resizeEvent = lambda event: (
            self.reposition_tag_filter_arrow(),
            QComboBox.resizeEvent(self.tag_filter_combo, event)
        )
    
        # --- Ligne 3 boutons : réindexer, réinitialiser, thème ---
        icons_layout = QHBoxLayout()

        # Boutons
        self.reindex_button = QPushButton()
        self.reindex_button.setIcon(qta.icon("fa5s.recycle", color="#007BFF"))
        self.reindex_button.setToolTip(self.t("tooltip_reindex"))
        self.reindex_button.clicked.connect(self.reindex_files)

        self.import_button = QPushButton()
        self.import_button.setIcon(qta.icon("fa5s.folder-plus", color="#007BFF"))
        self.import_button.setToolTip(self.t("tooltip_import"))
        self.import_button.clicked.connect(self.import_external_file_or_folder)

        self.reset_button = QPushButton()
        self.reset_button.setIcon(qta.icon("fa5s.sync", color="#007BFF"))
        self.reset_button.setToolTip(self.t("tooltip_refresh_ui"))
        self.reset_button.clicked.connect(self.refresh_ui)
        search_layout.addWidget(self.reset_button)

        # --- Bouton Numériser (scanner) ---
        self.scan_button = QPushButton()
        self.scan_button.setIcon(qta.icon("fa5s.file-import", color="#007BFF"))
        self.scan_button.setToolTip(self.t("tooltip_scan"))
        self.scan_button.clicked.connect(self._launch_scan_to_folder)

        # --- Bouton Information (à propos) ---
        self.info_button = QPushButton()
        self.info_button.setIcon(qta.icon("fa5s.info-circle", color="#007BFF"))
        self.info_button.setToolTip(self.t("tooltip_about"))
        self.info_button.clicked.connect(self.show_about_window)

        self.theme_button = QPushButton()
        self.theme_button.setIcon(qta.icon("fa5s.adjust", color="#007BFF"))
        self.theme_button.setToolTip(self.t("tooltip_theme"))
        self.theme_button.clicked.connect(self.toggle_theme)
                
        icon_button_style = (
            get_icon_button_style_dark()
            if self.current_theme == "dark"
            else get_icon_button_style_light()
        )

        for btn in [self.reindex_button, self.import_button, self.reset_button,
                    self.scan_button, self.info_button, self.theme_button]:
            btn.setStyleSheet(icon_button_style)
            btn.setFixedSize(40, 40)

        # Ajout dans le layout dans l'ordre voulu
        icons_layout.addWidget(self.reindex_button)
        icons_layout.addWidget(self.import_button)
        icons_layout.addWidget(self.reset_button)
        icons_layout.addWidget(self.scan_button)
        icons_layout.addWidget(self.info_button)
        icons_layout.addWidget(self.theme_button)
                
        left_layout.addLayout(icons_layout)
        left_layout.addSpacing(10)

        # --- progress bar ---
        self.init_progress_bar()

        # --- Arborescence des fichiers ---
        self.tree = DraggableTreeWidget(config.FILES_DIR)
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree.item_moved.connect(self._on_tree_item_moved)
        self.tree.external_drop.connect(self._on_tree_external_drop)
        left_layout.addWidget(self.tree)
        from styles import THEMES
        _t = THEMES.get(self.current_theme, THEMES["light"])
        self.tree.setItemDelegate(ScrollingItemDelegate(self.tree, _t["accent"]))
        self.tree._install_drag_filter()  # apres setItemDelegate

        # -- Zone de prévisualisation complète (avec sélecteur en haut) --
        self.preview_container = QWidget()
        self.preview_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Layout principal de la zone de prévisualisation
        self.preview_layout = QVBoxLayout(self.preview_container)
        #self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(5)
        
        # === Contenu principal de prévisualisation (stack) ===
        self.preview_frame = QFrame()
        #self.preview_frame.setObjectName("PreviewContent")
        #self.preview_frame.setStyleSheet("")
        #self.preview_frame.setFrameShape(QFrame.StyledPanel)
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.previewed_file_path = None

        frame_layout = QVBoxLayout(self.preview_frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)

        # Le stack reste ici
        self.preview_stack = QStackedLayout()
        frame_layout.addLayout(self.preview_stack)

        # Ajoute la frame au layout principal
        self.preview_layout.addWidget(self.preview_frame)

        # --- TEXTES ---
        self.text_preview = QTextEdit()
        self.text_preview.setStyleSheet(get_text_preview_style(self.current_theme))
        self.text_preview.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        self.text_preview.setReadOnly(True)
        self.text_preview.setFrameShape(QTextEdit.NoFrame)
        self.text_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.text_preview.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.text_preview.setContentsMargins(10, 10, 10, 10)

        # --- IMAGES ---
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_preview_label)
        self.image_scroll.viewport().setCursor(Qt.OpenHandCursor)
        self.image_scroll.viewport().installEventFilter(self)

        # --- HTML / WebEngine (instance UNIQUE — ne jamais recréer) ---
        # Plusieurs QWebEngineView simultanés → plusieurs contextes GPU → crash
        # sur Windows (SharedImageBackingFactory / Context lost).
        # On crée UN SEUL widget et on appelle setHtml()/setUrl() dessus.
        if WEB_ENGINE_AVAILABLE and QWebEngineView:
            self.html_preview = QWebEngineView()
            self.preview_stack.addWidget(self.html_preview)
        else:
            self.html_preview = None

        # --- XLS ---
        self.xlsx_tab_widget = QTabWidget()
        self.xlsx_tab_widget.setVisible(False)
        self.preview_stack.addWidget(self.xlsx_tab_widget)

        # Ajout des widgets à  la pile
        self.preview_stack.addWidget(self.text_preview)
        self.preview_stack.addWidget(self.image_scroll)

        # Navigateur de dossiers 
        self.folder_browser = FolderBrowserWidget(
            files_dir=config.FILES_DIR,
            theme=self.current_theme,
            translate=self.t,
        )
        # Connexion : clic sur un fichier dans le navigateur → prévisualisation
        self.folder_browser.file_activated.connect(self._on_folder_browser_file_clicked)
        # Connexion : navigation dans un sous-dossier → synchro panneau gauche
        self.folder_browser.folder_navigated.connect(self._on_folder_browser_navigated)
        self.folder_browser.print_requested.connect(self._print_file)
        self.preview_stack.addWidget(self.folder_browser)
        # fin navigateur de dossiers

        # Sélection par défaut
        self.preview_stack.setCurrentWidget(self.text_preview)

        # Ajout du preview_content_widget à l'interface
        self.preview_layout.addWidget(self.preview_frame)


        # === Barre de recherche Ctrl+F ===
        self.search_bar_widget = QWidget()
        self.search_bar_widget.setVisible(False)
        search_bar_layout = QHBoxLayout(self.search_bar_widget)
        search_bar_layout.setContentsMargins(6, 4, 6, 4)
        search_bar_layout.setSpacing(6)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText(self.t("find_placeholder") if "find_placeholder" in self.translations.get(self.current_language, {}) else "Rechercher...")
        self.find_input.setFixedHeight(28)
        self.find_input.setMinimumWidth(200)
        self.find_input.textChanged.connect(self._find_reset)

        self.find_prev_btn = QPushButton()
        self.find_prev_btn.setIcon(qta.icon("fa5s.chevron-up", color="#888"))
        self.find_prev_btn.setFixedSize(28, 28)
        self.find_prev_btn.setToolTip(self.t("find_prev") if "find_prev" in self.translations.get(self.current_language, {}) else "Précédent")
        self.find_prev_btn.clicked.connect(self._find_prev)

        self.find_next_btn = QPushButton()
        self.find_next_btn.setIcon(qta.icon("fa5s.chevron-down", color="#888"))
        self.find_next_btn.setFixedSize(28, 28)
        self.find_next_btn.setToolTip(self.t("find_next") if "find_next" in self.translations.get(self.current_language, {}) else "Suivant")
        self.find_next_btn.clicked.connect(self._find_next)

        self.find_count_label = QLabel("")
        self.find_count_label.setFixedWidth(90)
        self.find_count_label.setAlignment(Qt.AlignCenter)

        self.find_close_btn = QPushButton()
        self.find_close_btn.setIcon(qta.icon("fa5s.times", color="#888"))
        self.find_close_btn.setFixedSize(28, 28)
        self.find_close_btn.clicked.connect(self._close_search_bar)

        search_bar_layout.addWidget(self.find_input)
        search_bar_layout.addWidget(self.find_prev_btn)
        search_bar_layout.addWidget(self.find_next_btn)
        search_bar_layout.addWidget(self.find_count_label)
        search_bar_layout.addStretch()
        search_bar_layout.addWidget(self.find_close_btn)

        self.preview_layout.addWidget(self.search_bar_widget)

        # Raccourcis recherche
        self._find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._find_shortcut.activated.connect(self._toggle_search_bar)

        self._find_f3 = QShortcut(QKeySequence("F3"), self)
        self._find_f3.activated.connect(self._find_next)

        self._find_shift_f3 = QShortcut(QKeySequence("Shift+F3"), self)
        self._find_shift_f3.activated.connect(self._find_prev)

        self._find_alt_f3 = QShortcut(QKeySequence("Alt+F3"), self)
        self._find_alt_f3.activated.connect(self._find_prev)

        # Enter dans la barre de recherche = occurrence suivante
        self.find_input.returnPressed.connect(self._find_next)

        # Échap pour fermer
        self._find_esc = QShortcut(QKeySequence("Escape"), self.find_input)
        self._find_esc.activated.connect(self._close_search_bar)

        # === Contrôles de zoom + PDF + navigation regroupés ===
        self.zoom_controls_widget = QWidget()
        self.zoom_controls_layout = QHBoxLayout(self.zoom_controls_widget)  
        self.zoom_controls_layout.setContentsMargins(0, 0, 0, 0)

        # -- bouton de rotation --
        self.rotate_button = QPushButton()
        self.rotate_button.setObjectName("RotateButton")
        self.rotate_button.setIcon(qta.icon("fa5s.redo", color="#007BFF"))  
        self.rotate_button.setToolTip("Rotation de l'image")
        self.rotate_button.clicked.connect(self.rotate_image)  # Connecte la fonction de rotation
        
        # -- bouton précédent --
        self.prev_page_button = QPushButton()
        self.prev_page_button.setObjectName("PrevPageButton")
        self.prev_page_button.setIcon(qta.icon("fa5s.arrow-left", color="#007BFF"))
        self.prev_page_button.setToolTip("Page précédente")
        self.prev_page_button.clicked.connect(self.previous_pdf_page)

        # -- bouton suivant --
        self.next_page_button = QPushButton()
        self.next_page_button.setObjectName("NextPageButton")
        self.next_page_button.setIcon(qta.icon("fa5s.arrow-right", color="#007BFF"))
        self.next_page_button.setToolTip("Page suivante")
        self.next_page_button.clicked.connect(self.next_pdf_page)

        # -- Zoom + --
        self.zoom_in_button = QPushButton()
        self.zoom_in_button.setObjectName("ZoomInButton")
        self.zoom_in_button.setIcon(qta.icon("fa5s.search-plus", color="#007BFF"))
        self.zoom_in_button.setToolTip("Zoom avant")
        self.zoom_in_button.clicked.connect(self.zoom_in)

        # -- Zoom - --
        self.zoom_out_button = QPushButton()
        self.zoom_out_button.setObjectName("ZoomOutButton")
        self.zoom_out_button.setIcon(qta.icon("fa5s.search-minus", color="#007BFF"))
        self.zoom_out_button.setToolTip("Zoom arrière")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        for btn in [self.prev_page_button, self.next_page_button, self.rotate_button, self.zoom_in_button, self.zoom_out_button]:
            btn.setFixedSize(32, 32)

        # -- Zoom label --
        self.zoom_label = QLabel("Zoom : 100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_controls_layout.addWidget(self.zoom_label)  
        
        self.zoom_controls_layout.addSpacing(20)
        
        # Organisation dans le layout
        self.zoom_controls_layout.addWidget(self.prev_page_button)
        self.zoom_controls_layout.addStretch(1)
        self.zoom_controls_layout.addWidget(self.rotate_button)
        self.zoom_controls_layout.addWidget(self.zoom_in_button)
        self.zoom_controls_layout.addWidget(self.zoom_out_button)
        self.zoom_controls_layout.addWidget(self.zoom_label)
        self.zoom_controls_layout.addStretch(1)
        self.zoom_controls_layout.addWidget(self.next_page_button)

        # -- Bouton Imprimer (prévisualisation) --
        self.preview_print_button = QPushButton()
        self.preview_print_button.setObjectName("PreviewPrintButton")
        self.preview_print_button.setIcon(qta.icon("fa5s.print", color="#007BFF"))
        self.preview_print_button.setToolTip(self.t("tooltip_print") if "tooltip_print" in
            self.translations.get(self.current_language, {}) else "Imprimer")
        self.preview_print_button.setFixedSize(32, 32)
        self.preview_print_button.clicked.connect(self._print_previewed_file)
        self.zoom_controls_layout.addSpacing(12)
        self.zoom_controls_layout.addWidget(self.preview_print_button)

        # sélecteur de page PDF
        self.top_page_selector = QComboBox()
        self.top_page_selector.setFixedWidth(130)
        self.top_page_selector.setVisible(False)
        self.top_page_selector.setEnabled(False)
        self.top_page_selector.currentIndexChanged.connect(self.go_to_pdf_page_from_top)
        self.top_page_selector.setEditable(True)
        self.top_page_selector.lineEdit().setAlignment(Qt.AlignCenter)
        self.top_page_selector.setEditable(False)

        # Conteneur avec layout centré en haut
        self.top_selector_widget = QWidget()
        self.top_selector_widget.setFixedHeight(50)
        top_selector_layout = QHBoxLayout(self.top_selector_widget)
        top_selector_layout.setContentsMargins(0, 0, 0, 0)
        top_selector_layout.addStretch()
        top_selector_layout.addWidget(self.top_page_selector)
        top_selector_layout.addStretch()

        self.top_selector_widget.setVisible(False)  # MASQUÃ‰ PAR DÃ‰FAUT
        self.preview_layout.insertWidget(0, self.top_selector_widget)


        self.preview_layout.addWidget(self.zoom_controls_widget)
        self.zoom_controls_widget.hide()

        # === Bouton Métadonnées ===
        self.toggle_metadata_button = QPushButton(f" {self.t('button_metadata')}")
        self.toggle_metadata_button.setCheckable(True)
        self.toggle_metadata_button.setChecked(False)
        self.toggle_metadata_button.setIcon(qta.icon("fa5s.angle-down", color="#007BFF"))
        self.toggle_metadata_button.clicked.connect(self.toggle_metadata_visibility)
        self.toggle_metadata_button.setStyleSheet(get_metadata_toggle_button_style(self.current_theme))
        self.preview_layout.addWidget(self.toggle_metadata_button)

        # === Formulaire Métadonnées ===
        self.metadata_form = QWidget()
        self.metadata_layout = QGridLayout(self.metadata_form)
        self.metadata_layout.setContentsMargins(4, 2, 4, 2)
        self.metadata_layout.setHorizontalSpacing(8)
        self.metadata_layout.setVerticalSpacing(6)

        self.metadata_animation = QPropertyAnimation(self.metadata_form, b"maximumHeight")
        self.metadata_animation.setDuration(400)
        self.metadata_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.metadata_animation.finished.connect(self.on_metadata_animation_finished)

        self.metadata_form.setStyleSheet(get_metadata_form_style(self.current_theme))

        self.meta_author_field = QLineEdit()

        # === TAGS ===
        self.setup_metadata_tags_field()

        self.meta_comment_field = QTextEdit()
        self.meta_comment_field.setMinimumHeight(52)
        self.meta_comment_field.setMaximumHeight(100)
        self.meta_version_field = QLineEdit()
        self.meta_updated_field = QLineEdit()
        self.meta_updated_field.setReadOnly(True)

        self.meta_author_field.setMinimumHeight(26)
        self.meta_version_field.setMinimumHeight(26)
        self.meta_updated_field.setMinimumHeight(26)

        self.label_author = QLabel(self.t("label_author"))
        self.metadata_layout.addWidget(self.label_author, 0, 0)
        self.metadata_layout.addWidget(self.meta_author_field, 0, 1)
        # meta_tags_container déjà ajouté dans setup_metadata_tags_field() (ligne 1, col 0 et 1)
        self.label_comment = QLabel(self.t("label_comment"))
        self.metadata_layout.addWidget(self.label_comment, 2, 0)
        self.metadata_layout.addWidget(self.meta_comment_field, 2, 1)
        self.label_version = QLabel(self.t("label_version"))
        self.metadata_layout.addWidget(self.label_version, 3, 0)
        self.metadata_layout.addWidget(self.meta_version_field, 3, 1)
        self.label_updated = QLabel(self.t("label_updated"))
        self.metadata_layout.addWidget(self.label_updated, 4, 0)
        self.metadata_layout.addWidget(self.meta_updated_field, 4, 1)

        self.save_metadata_button = QPushButton(self.t("button_save_metadata"))
        self.save_metadata_button.setObjectName("saveMetadataButton")
        self.save_metadata_button.clicked.connect(self.save_current_metadata)
        self.metadata_layout.addWidget(self.save_metadata_button, 5, 0, 1, 2)
        self.save_metadata_button.setStyleSheet(get_save_button_style())
        self.save_confirmation_label = QLabel("")
        self.save_confirmation_label.setStyleSheet(get_save_confirmation_label_style())
        self.save_confirmation_label.hide()
        self.metadata_layout.addWidget(self.save_confirmation_label, 6, 0, 1, 2)

        # Scroll container uniquement
        self.metadata_form.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.preview_layout.addWidget(self.metadata_form)
        self.metadata_form.hide()

        self.metadata_form.hide()

        # -- Splitter principal --
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setHandleWidth(2)
        self.splitter.setSizes([250, 950])

        # Restaurer la taille sauvegardée (avec garde-fous)
        saved_cfg = config.load_config()
        saved_splitter = saved_cfg.get("splitter_sizes")
        if (saved_splitter and len(saved_splitter) == 2
                and 80 <= saved_splitter[0] <= 600
                and saved_splitter[1] > 100):
            self.splitter.setSizes(saved_splitter)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.setCentralWidget(container)

        # -- Bouton accordéon flottant (enfant du container, à cheval sur le splitter) --
        self._sidebar_open   = True
        self._sidebar_saved  = 250
        self._sidebar_anim   = None

        self._sidebar_btn = QPushButton(container)
        self._sidebar_btn.setFixedSize(26, 26)
        self._sidebar_btn.setCursor(Qt.PointingHandCursor)
        self._sidebar_btn.setToolTip("Réduire / Afficher le panneau")
        self._sidebar_btn.clicked.connect(self._toggle_sidebar)
        self._sidebar_btn.raise_()
        self._update_sidebar_btn_style()
        self._update_sidebar_btn_icon()

        # Repositionner après que le layout soit effectif
        QTimer.singleShot(0, self._reposition_sidebar_btn)
        self.splitter.splitterMoved.connect(lambda *_: self._reposition_sidebar_btn())

        # --- Barre de boutons supplémentaires en bas ---
        bottom_buttons_layout = QHBoxLayout()

        btn_style = get_bottom_button_style(self.current_theme)

        # Bouton Supprimer
        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon("fa5s.trash", color="#007BFF"))
        self.delete_button.setToolTip(self.t("tooltip_delete"))
        self.delete_button.setFixedSize(40, 40)
        self.delete_button.setStyleSheet(btn_style)
        self.delete_button.clicked.connect(self.delete_selected_items)
        bottom_buttons_layout.addWidget(self.delete_button)

        # Bouton Renommer
        self.rename_button = QPushButton()
        self.rename_button.setIcon(qta.icon("fa5s.i-cursor", color="#007BFF"))
        self.rename_button.setToolTip(self.t("tooltip_rename"))
        self.rename_button.setFixedSize(40, 40)
        self.rename_button.setStyleSheet(btn_style)
        self.rename_button.clicked.connect(self.rename_selected_item)
        bottom_buttons_layout.addWidget(self.rename_button)

        # Bouton Statistiques
        self.stats_button = QPushButton()
        self.stats_button.setIcon(qta.icon("fa5s.chart-bar", color="#007BFF"))
        self.stats_button.setToolTip(self.t("tooltip_stats"))
        self.stats_button.setFixedSize(40, 40)
        self.stats_button.setStyleSheet(btn_style)
        self.stats_button.clicked.connect(self.show_ged_statistics)
        bottom_buttons_layout.addWidget(self.stats_button)

        # Bouton Sauvegarde (propre, sans flèche)
        self.backup_button = QPushButton()
        self.backup_button.setIcon(qta.icon("fa5s.archive", color="#007BFF"))
        self.backup_button.setToolTip(self.t("tooltip_backup"))
        self.backup_button.setFixedSize(40, 40)
        self.backup_button.setStyleSheet(btn_style)
        self.backup_button.clicked.connect(self.show_backup_menu)
        bottom_buttons_layout.addWidget(self.backup_button)


        # Bouton Quitter (en rouge)
        self.quit_button = QPushButton()
        self.quit_button.setIcon(qta.icon("fa5s.sign-out-alt", color="red"))
        self.quit_button.setToolTip(self.t("tooltip_quit"))
        self.quit_button.setFixedSize(40, 40)
        self.quit_button.setStyleSheet(btn_style)
        self.quit_button.clicked.connect(self.close)
        bottom_buttons_layout.addWidget(self.quit_button)

        left_layout.addLayout(bottom_buttons_layout)

        # -- Initialisation --
        self.locked_symlinks = config.load_locked_symlinks()
        self.update_file_count()
        self.load_documents()
        self.apply_theme(self.current_theme)
        

    def closeEvent(self, event):
        """Sauvegarde la géométrie et la taille du splitter avant fermeture."""
        try:
            cfg = config.load_config()
            g = self.geometry()
            cfg["window_geometry"]  = [g.x(), g.y(), g.width(), g.height()]
            # Ne sauvegarder que si le panneau est ouvert (évite de sauver 0)
            if self._sidebar_open:
                cfg["splitter_sizes"] = self.splitter.sizes()
            config.save_config(cfg)
        except Exception as e:
            print(f"[WARN] closeEvent save: {e}")
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_sidebar_btn"):
            QTimer.singleShot(0, self._reposition_sidebar_btn)

    def update_logo(self):
        logo_path = config.get_logo_path(self.current_theme)
        
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaledToWidth(160, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("KO")
    
    def init_progress_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)

        self.progress_label = QLabel("")  # â† nouveau label texte
        self.progress_label.setVisible(False)

        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().addPermanentWidget(self.progress_label)

    
    def _update_progress_value(self, val, total):
        if not self._is_searching:
            return

        try:
            if total == 0:
                return

            percent = min(int(val / total * 100), 100)

            if self.progress_bar:
                self.progress_bar.blockSignals(True)
                self.progress_bar.setMaximum(total)
                self.progress_bar.setValue(val)
                self.progress_bar.blockSignals(False)

            if hasattr(self, "progress_label") and self.progress_label:
                self.progress_label.setText(f"{val}/{total} ({percent}%)")
                self.progress_label.setVisible(True)

            # Ne pas appeler processEvents ici !
            # QApplication.processEvents()

        except RecursionError:
            print("[FATAL] Boucle récursive détectée dans _update_progress_value()")
        except Exception as e:
            print(f"[ERREUR] _update_progress_value : {e}")

    def hide_progress_bar_fade(self):
        anim = QPropertyAnimation(self.progress_bar, b"windowOpacity")
        anim.setDuration(1000)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)

        def after_hide():
            self.progress_bar.setVisible(False)
            self.progress_bar.setWindowOpacity(1.0)
            self.progress_label.setVisible(False)  #  cacher le label

        anim.finished.connect(after_hide)
        anim.start()
        self._progress_anim = anim

    
    def show_progress_bar_fade(self):
        self.progress_bar.setWindowOpacity(0.0)
        self.progress_bar.setVisible(True)
        anim = QPropertyAnimation(self.progress_bar, b"windowOpacity")
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._progress_show_anim = anim
    
    def show_search_progress(self):
        self.progress_label.setText(self.t("search_in_progress"))
        self.progress_label.setVisible(True)
        self.progress_bar.setMaximum(0)  # Mode indéterminé (barre qui "tourne")
        self.progress_bar.setVisible(True)
        QApplication.processEvents()
    
    def hide_search_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progress_bar.setMaximum(100)  # Réinitialise en mode déterminé

    def update_window_title(self, filename: str = None):
        # 1) l'icône de la fenêtre devient le drapeau
        flag_icon = get_flag_icon(self.current_language)
        self.setWindowIcon(flag_icon)

        # 2) on assemble le texte
        title = "LibreGED v.2.9.1"
        if filename:
            title += f" – {filename}"
        self.setWindowTitle(title)

    def t(self, key):
        return self.translations.get(self.current_language, {}).get(key, key)


    def show_preview_widget(self, widget):
        """Affiche le widget voulu dans le QStackedLayout de prévisualisation."""
        index = self.preview_stack.indexOf(widget)
        if index != -1:
            self.preview_stack.setCurrentIndex(index)

    def go_to_pdf_page_from_top(self, index):
        if not hasattr(self, "pdf_doc") or not self.pdf_doc:
            return
        self.current_pdf_page = index
        self.render_current_pdf_page()

    def load_documents(self):
        self.tree.clear()

        root_items = {}  # Chemins des dossiers
        top_items = []   # Références aux éléments racine (à injecter plus tard)

        # 1. Collecte tous les chemins depuis la base
        all_docs = fetch_all_documents()
        rel_paths = [Path(doc[2]) for doc in all_docs]

        # 2. Dossiers parents des fichiers indexes
        folder_paths = set()
        for path in rel_paths:
            folder_paths.update(list(path.parents))  # list() requis Python 3.12+
            folder_paths.add(path.parent)

        # 2b. Scan filesystem : inclut aussi les dossiers sans fichiers
        for root, dirs, _ in os.walk(config.FILES_DIR, followlinks=True):
            for d in dirs:
                abs_dir = Path(root) / d
                try:
                    rel = _safe_rel(abs_dir, config.FILES_DIR)
                    if rel:
                        folder_paths.add(Path(rel))
                except (ValueError, OSError):
                    pass

        folder_paths = {p for p in folder_paths if str(p) != "."}
        sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

        # 3. Crée les dossiers dans l'arborescence
        for folder in sorted_folders:
            parts = folder.parts
            parent = None
            path_accumulator = []

            for i, part in enumerate(parts):
                path_accumulator.append(part)
                current_path = os.sep.join(path_accumulator)

                if current_path not in root_items:
                    folder_item = QTreeWidgetItem([part])
                    folder_full_path = config.FILES_DIR / current_path

                    # Vérifie si le dossier est un lien symbolique
                    is_symlink = _is_symlink_robust(folder_full_path)
                    icon_color = "#00A2FF" if is_symlink else "#0078D7"
                    folder_item.setIcon(0, get_folder_icon(color=icon_color))

                    folder_item.setFlags(folder_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, current_path)
                    folder_item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
                    root_items[current_path] = folder_item

                    if parent:
                        parent.addChild(folder_item)
                    else:
                        top_items.append(folder_item)
                parent = root_items[current_path]

        # 4. Ajoute les fichiers (en ignorant les .keep et .json)
        for doc in all_docs:
            rel_path = doc[2]
            abs_path = config.FILES_DIR / rel_path

            if abs_path.name == ".keep" or rel_path.endswith(".json"):
                continue

            parts = rel_path.split(os.sep)
            parent = None
            path_accumulator = []

            for i, part in enumerate(parts):
                path_accumulator.append(part)
                current_path = os.sep.join(path_accumulator)

                if i == len(parts) - 1:
                    file_item = QTreeWidgetItem([part])
                    ext = os.path.splitext(rel_path)[1]

                    # Vérifie si le fichier est un lien symbolique
                    is_symlink = _is_symlink_robust(abs_path)
                    icon_color = "#00A2FF" if is_symlink else "#0078D7"
                    file_item.setIcon(0, get_icon_for_extension(ext, self.current_theme, color=icon_color))

                    file_item.setData(0, Qt.ItemDataRole.UserRole, rel_path)
                    file_item.setData(0, Qt.ItemDataRole.UserRole + 1, "file")

                    if parent:
                        parent.addChild(file_item)
                    else:
                        top_items.append(file_item)
                else:
                    parent = root_items.get(current_path)

        # 5. Tri recursif : dossiers en premier, fichiers ensuite
        def sort_tree_items_recursively(item):
            children = [item.child(i) for i in range(item.childCount())]
            children.sort(key=lambda x: (
                0 if x.data(0, Qt.ItemDataRole.UserRole + 1) == "folder" else 1,
                x.text(0).lower()
            ))
            for i in reversed(range(item.childCount())):
                item.takeChild(i)
            for child in children:
                item.addChild(child)
                sort_tree_items_recursively(child)

        top_items.sort(key=lambda x: (
            0 if x.data(0, Qt.ItemDataRole.UserRole + 1) == "folder" else 1,
            x.text(0).lower()
        ))
        for item in top_items:
            sort_tree_items_recursively(item)
            self.tree.addTopLevelItem(item)

        self.set_metadata_fields_enabled(False)


            
    def update_file_count(self):
        from database.db import fetch_all_documents  
        
        docs = fetch_all_documents()

        # Filtrer pour exclure les fichiers .json
        count = len([doc for doc in docs if not doc[2].endswith('.json')])

        self.file_count_label.setText(self.t("file_count_label").format(count=count))


    def clear_preview(self):
        self.text_preview.hide()
        self.image_scroll.hide()
        self.zoom_controls_widget.hide()
        self.prev_page_button.hide()
        self.next_page_button.hide()
        self.xlsx_tab_widget.setVisible(False)
        self.top_page_selector.setVisible(False)  
        self.previewed_file_path = None
        self.update_file_info_label_state(False)

        if self.html_preview:
            self.html_preview.hide()

        display_text = item.text()
        
        rel_path = item.data(0, Qt.ItemDataRole.UserRole)
            
        if not rel_path:
            self.show_text_preview(self.t("error_missing_path"))
            return

        doc_path = config.FILES_DIR / rel_path  
        
        if not path_exists(doc_path):
            self.show_text_preview(self.t("error_file_not_found"))
            return
        
        ext = doc_path.suffix.lower().strip()

        try:
            if ext in [".html", ".htm"]:
                if WEB_ENGINE_AVAILABLE and self.html_preview:
                    try:
                        self.html_preview.setVisible(True)
                        self._webview_load_url(QUrl.fromLocalFile(str(doc_path)))
                    except Exception as e:
                        self.show_text_preview(self.t("error_loading_html").format(error=str(e)))
                else:
                    try:
                        with open(win_path(doc_path), "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        self.text_preview.setPlainText(content)
                        self.text_preview.setVisible(True)
                    except Exception as e:
                        self.show_text_preview(self.t("error_reading_html").format(error=str(e)))

            elif ext in [".txt", ".md", ".py"]:
                with open(win_path(doc_path), "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.show_text_preview(content)

            elif ext == ".pdf":
                self.pdf_doc = fitz.open(win_path(doc_path))
                self.current_pdf_page = 0
                self.current_zoom = 1.0
                self.render_current_pdf_page(adapt_to_width=True)

                page_count = self.pdf_doc.page_count
                print(f"[DEBUG] PDF détecté avec {page_count} pages")

                if page_count > 1:
                    self.top_page_selector.blockSignals(True)
                    self.top_page_selector.clear()
                    for i in range(page_count):
                        icon = qta.icon("fa5.file-alt", color="#007BFF")  # ou "fa.file", "fa5s.file", etc.
                        self.top_page_selector.addItem(icon, f"{self.t('page')} {i + 1}")
                        #self.top_page_selector.addItem(f"Page {i + 1}")
                    self.top_page_selector.setCurrentIndex(0)
                    self.top_page_selector.setVisible(True)
                    self.top_page_selector.setEnabled(True)
                    self.top_page_selector.blockSignals(False)
                    self.top_selector_widget.setVisible(True)  
                else:
                    self.top_page_selector.clear()
                    self.top_page_selector.setVisible(False)
                    self.top_page_selector.setEnabled(False)
                    self.top_selector_widget.setVisible(False)  

            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"]:
                try:
                    image = Image.open(win_path(doc_path))
                    try:
                        for orientation in ExifTags.TAGS.keys():
                            if ExifTags.TAGS[orientation] == 'Orientation':
                                break
                        exif = dict(image._getexif().items())
                        orientation_value = exif.get(orientation, None)
                        if orientation_value == 3:
                            image = image.rotate(180, expand=True)
                        elif orientation_value == 6:
                            image = image.rotate(270, expand=True)
                        elif orientation_value == 8:
                            image = image.rotate(90, expand=True)
                    except Exception as exif_err:
                        print(f"[INFO] Aucune orientation EXIF ou erreur : {exif_err}")

                    image = image.convert("RGBA")
                    data = image.tobytes("raw", "RGBA")
                    qim = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qim)

                    if pixmap.isNull():
                        self.show_text_preview(self.t("error_invalid_image"))
                    else:
                        self.pdf_doc = None
                        self.current_zoom = 1.0
                        self.show_image_preview(pixmap)

                except Exception as e:
                    QMessageBox.critical(self, self.t("error_loading_image"), str(e))

            elif ext == ".epub":
                self.show_epub_preview(doc_path)

            elif ext == ".docx":
                html = self.show_docx_preview(doc_path)
                if html:
                    self.show_html_preview(html)

            elif ext == ".odt":
                html = odf_utils.odt_to_html(win_path(doc_path))
                self.show_html_preview(html)
            
            elif ext in [".xlsx", ".xlsm"]:
                self.show_xlsx_preview(doc_path)

            elif ext == ".pptx":
                content = odf_utils.extract_text_from_pptx(doc_path)
                self.show_text_preview(content if content else self.t("textfile_read_error").format(error=""))

            else:
                self.show_text_preview(self.t("error_unsupported"))

        except Exception as e:
            QMessageBox.critical(self, self.t("error_reading_file"), str(e))
    
    ###################################### VERSION 2.3 #################################
    def open_tree_context_menu(self, position):
        selected_item = self.tree.itemAt(position)
        if not selected_item:
            return

        file_rel_path = selected_item.data(0, Qt.UserRole)
        file_abs_path = config.FILES_DIR / file_rel_path

        menu = QMenu(self)

        if _is_symlink_robust(file_abs_path):
            open_original_action = menu.addAction(self.t("open_original_folder"))
            open_original_action.triggered.connect(lambda: self.open_real_folder(file_abs_path))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    # ─────────────────────────────────────────────────────────────────
    # Recherche Ctrl+F dans la prévisualisation
    # ─────────────────────────────────────────────────────────────────

    def _schedule_search_highlight(self):
        """Surligue le terme de la barre de recherche selon le widget actif."""
        query = self.search_input.text().strip()
        if not query:
            return
        keywords = [kw for kw in query.replace(",", " ").split() if kw]
        if not keywords:
            return
        term = keywords[0]

        current = self.preview_stack.currentWidget()

        # QTextEdit (TXT, MD, code...)
        if current is self.text_preview:
            self._highlight_term_in_text_preview(term)

        # QWebEngineView (HTML, DOCX, ODT, EPUB, MHTML, EML...)
        elif self.html_preview and current is self.html_preview:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(250, lambda t=term: self._highlight_term_in_webengine(t))

        # QTableWidget via QTabWidget (XLSX, XLSM)
        elif current is self.xlsx_tab_widget:
            self._highlight_term_in_xlsx(term)

        # QPixmap (PDF rendu via fitz)
        elif current is self.image_scroll and hasattr(self, "pdf_doc") and self.pdf_doc:
            self._highlight_term_in_pdf(term)

    def _highlight_term_in_xlsx(self, term: str):
        """Surligne les cellules correspondantes dans le QTableWidget XLSX."""
        from styles import THEMES
        from PySide6.QtGui import QBrush
        t_palette = THEMES.get(self.current_theme, THEMES["light"])
        accent = QColor("#FFD600")   # jaune vif
        accent.setAlpha(220)
        text_color = QColor("#1A1A1A")
        term_lower = term.lower()

        table = self.xlsx_tab_widget.currentWidget()
        if not isinstance(table, QTableWidget):
            return

        first_match = None
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is None:
                    continue
                if term_lower in item.text().lower():
                    item.setBackground(QBrush(accent))
                    item.setForeground(QBrush(text_color))
                    if first_match is None:
                        first_match = item
                else:
                    item.setBackground(QBrush())  # reset
                    item.setForeground(QBrush())

        if first_match:
            table.scrollToItem(first_match)

    def _highlight_term_in_pdf(self, term: str):
        """Surligne les occurrences texte sur la page PDF courante via PyMuPDF + QPainter."""
        if not self.pdf_doc or not self.original_pixmap or not term:
            return
        try:
            from PySide6.QtGui import QPainter, QBrush, QPen
            from styles import THEMES
            t_palette = THEMES.get(self.current_theme, THEMES["light"])
            accent = QColor("#FFD600")   # jaune vif
            accent.setAlpha(160)

            page = self.pdf_doc.load_page(self.current_pdf_page)
            rects = page.search_for(term)
            if not rects:
                return

            # Facteur d'échelle fitz → pixmap
            scale_x = self.original_pixmap.width()  / page.rect.width
            scale_y = self.original_pixmap.height() / page.rect.height

            # Peindre les overlays sur une copie du pixmap
            highlighted = self.original_pixmap.copy()
            painter = QPainter(highlighted)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(accent))
            painter.setPen(QPen(Qt.NoPen))

            from PySide6.QtCore import QRectF
            for r in rects:
                x = r.x0 * scale_x
                y = r.y0 * scale_y
                w = (r.x1 - r.x0) * scale_x
                h = (r.y1 - r.y0) * scale_y
                painter.drawRoundedRect(QRectF(x, y, w, h), 2, 2)

            painter.end()

            # Remplacer le pixmap affiché (sans toucher à original_pixmap)
            scaled = highlighted.scaled(
                int(highlighted.width() * self.current_zoom),
                int(highlighted.height() * self.current_zoom),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_preview_label.setPixmap(scaled)
            self.image_preview_label.adjustSize()

        except Exception as e:
            print(f"[WARN] PDF highlight: {e}")

    def _highlight_term_in_text_preview(self, term: str):
        """Surligne toutes les occurrences d'un terme dans QTextEdit."""
        from styles import THEMES
        t_palette = THEMES.get(self.current_theme, THEMES["light"])
        accent = t_palette["accent"]

        doc = self.text_preview.document()
        text_lower = doc.toPlainText().lower()
        term_lower = term.lower()

        positions = []
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1

        if not positions:
            return

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FFD600"))
        fmt.setForeground(QColor("#1A1A1A"))

        extra_selections = []
        for pos in positions:
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(term))
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            extra_selections.append(sel)

        self.text_preview.setExtraSelections(extra_selections)

        # Scroller vers la première occurrence
        if positions:
            cursor = QTextCursor(doc)
            cursor.setPosition(positions[0])
            self.text_preview.setTextCursor(cursor)
            self.text_preview.ensureCursorVisible()

    def _highlight_term_in_webengine(self, term: str):
        """Surligne le terme dans QWebEngineView via findText natif."""
        if self.html_preview:
            try:
                self.html_preview.page().findText(term)
            except Exception:
                pass

    def _toggle_search_bar(self):
        """Affiche ou masque la barre de recherche."""
        visible = self.search_bar_widget.isVisible()
        if visible:
            self._close_search_bar()
        else:
            self._apply_search_bar_style()
            self.search_bar_widget.setVisible(True)
            self.find_input.setFocus()
            self.find_input.selectAll()

    def _apply_search_bar_style(self):
        """Applique le style de la barre selon le thème courant."""
        from styles import THEMES
        t = THEMES.get(self.current_theme, THEMES["light"])
        self.search_bar_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {t['surface2']};
                border-top: 1px solid {t['border']};
                border-radius: 0px;
            }}
            QLineEdit {{
                background-color: {t['surface']};
                color: {t['text']};
                border: 1.5px solid {t['border']};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {t['accent']}; }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {t['hover']}; }}
            QLabel {{ color: {t['text_secondary']}; font-size: 11px; background: transparent; }}
        """)

    def _close_search_bar(self):
        """Ferme la barre et efface les surbrillances."""
        self.search_bar_widget.setVisible(False)
        self.find_input.clear()
        self._clear_highlights()
        # Réinitialiser le cache XLSX pour la prochaine ouverture
        self._xlsx_find_cache = None
        self._xlsx_find_index = -1

    def _find_reset(self):
        """Relance la recherche depuis le début dès que le texte change."""
        self.find_count_label.setText("")
        # Réinitialiser le cache XLSX (nouveau terme)
        self._xlsx_find_cache = None
        self._xlsx_find_index = -1
        self._do_find(forward=True, reset=True)

    def _find_next(self):
        self._do_find(forward=True)

    def _find_prev(self):
        self._do_find(forward=False)

    def _do_find(self, forward: bool = True, reset: bool = False):
        """Lance la recherche Ctrl+F selon le widget actif dans preview_stack."""
        query = self.find_input.text().strip()
        if not query:
            self._clear_highlights()
            self.find_count_label.setText("")
            return

        current = self.preview_stack.currentWidget()

        # ── QTextEdit (TXT, MD, code…) ────────────────────────────────────
        if current is self.text_preview:
            self._highlight_in_text_preview(query, forward, reset)
            return

        # ── QWebEngineView (HTML, DOCX, ODT, EPUB, MHTML, EML, SVG…) ─────
        # On compare par type car html_preview peut avoir été recréé
        if isinstance(current, QWebEngineView):
            from PySide6.QtWebEngineCore import QWebEnginePage
            flags = QWebEnginePage.FindFlag(0) if forward else QWebEnginePage.FindBackward
            current.page().findText(
                query, flags,
                lambda found: self.find_count_label.setText(
                    "Trouvé" if found else "0 résultat"
                )
            )
            return

        # ── QTabWidget XLSX / ODS ─────────────────────────────────────────
        if current is self.xlsx_tab_widget:
            self._find_in_xlsx(query, forward, reset)
            return

        # ── PDF (image_scroll) ────────────────────────────────────────────
        if current is self.image_scroll and hasattr(self, "pdf_doc") and self.pdf_doc:
            self._highlight_term_in_pdf(query)
            self.find_count_label.setText(
                "Trouvé" if query else "0 résultat"
            )
            return

    def _find_in_xlsx(self, query: str, forward: bool, reset: bool):
        """
        Recherche et navigation (suivant/précédent) dans le QTableWidget XLSX actif.
        """
        from PySide6.QtGui import QBrush
        accent     = QColor("#FFD600")
        accent.setAlpha(220)
        text_color = QColor("#1A1A1A")

        table = self.xlsx_tab_widget.currentWidget()
        if not isinstance(table, QTableWidget):
            self.find_count_label.setText("0 résultat")
            return

        query_lower = query.lower()

        # Reconstruire la liste des correspondances si le terme ou la feuille a changé
        cache_key = (id(table), query_lower)
        if reset or not hasattr(self, "_xlsx_find_cache") or self._xlsx_find_cache[0] != cache_key:
            matches = []
            for row in range(table.rowCount()):
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item and query_lower in item.text().lower():
                        matches.append((row, col))
            self._xlsx_find_cache   = (cache_key, matches)
            self._xlsx_find_index   = 0 if matches else -1
        else:
            _, matches = self._xlsx_find_cache
            if matches:
                if forward:
                    self._xlsx_find_index = (self._xlsx_find_index + 1) % len(matches)
                else:
                    self._xlsx_find_index = (self._xlsx_find_index - 1) % len(matches)

        # Réinitialiser tous les fonds
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setBackground(QBrush())
                    item.setForeground(QBrush())

        if not matches:
            self.find_count_label.setText("0 résultat")
            return

        # Surligner toutes les occurrences
        bg_all = QColor("#FFF59D"); bg_all.setAlpha(200)
        for row, col in matches:
            item = table.item(row, col)
            if item:
                item.setBackground(QBrush(bg_all))
                item.setForeground(QBrush(text_color))

        # Occurrence courante en jaune vif
        cur_row, cur_col = matches[self._xlsx_find_index]
        cur_item = table.item(cur_row, cur_col)
        if cur_item:
            cur_item.setBackground(QBrush(accent))
            table.scrollToItem(cur_item)
            table.setCurrentItem(cur_item)

        count = len(matches)
        self.find_count_label.setText(f"{self._xlsx_find_index + 1} / {count}")

    def _highlight_in_text_preview(self, query: str, forward: bool, reset: bool):
        """Surligne toutes les occurrences dans QTextEdit et navigue entre elles."""
        from styles import THEMES
        t = THEMES.get(self.current_theme, THEMES["light"])
        accent = t["accent"]

        doc = self.text_preview.document()
        text = doc.toPlainText()
        query_lower = query.lower()
        text_lower = text.lower()

        # Trouver toutes les positions
        positions = []
        start = 0
        while True:
            idx = text_lower.find(query_lower, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1

        count = len(positions)
        if count == 0:
            self._clear_highlights()
            self.find_count_label.setText(
                self.t("find_not_found") if "find_not_found" in self.translations.get(self.current_language, {})
                else "0 résultat"
            )
            return

        # Colorer toutes les occurrences
        extra_selections = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FFD600"))   # jaune vif
        fmt.setForeground(QColor("#1A1A1A"))   # texte sombre lisible

        for pos in positions:
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(query))
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            extra_selections.append(sel)

        self.text_preview.setExtraSelections(extra_selections)

        # Gérer l'index de navigation
        if not hasattr(self, "_find_index") or reset:
            self._find_index = 0
        else:
            if forward:
                self._find_index = (self._find_index + 1) % count
            else:
                self._find_index = (self._find_index - 1) % count

        # Scroller vers l'occurrence courante
        cursor = QTextCursor(doc)
        cursor.setPosition(positions[self._find_index])
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(query))
        self.text_preview.setTextCursor(cursor)
        self.text_preview.ensureCursorVisible()

        self.find_count_label.setText(f"{self._find_index + 1} / {count}")

    def _clear_highlights(self):
        """Efface toutes les surbrillances."""
        if hasattr(self, "text_preview"):
            self.text_preview.setExtraSelections([])
        if self.html_preview:
            try:
                self.html_preview.page().findText("")
            except Exception:
                pass

    def open_real_folder(self, symlink_path: Path):
        try:
            real_path = symlink_path.resolve(strict=True)
            folder = real_path.parent
            if folder.exists():
                import subprocess
                from database.path_utils import _clean_env_for_subprocess
                subprocess.Popen(["xdg-open", str(folder)], env=_clean_env_for_subprocess())
            else:
                QMessageBox.warning(self, "Erreur", "Le dossier cible n'existe plus.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible dâ€™ouvrir le dossier :\n{e}")



    #################################### FIN VERSION 2.3 ###############################


    def show_epub_preview(self, file_path):
        try:
            from tempfile import NamedTemporaryFile
            import base64

            book = epub.read_epub(str(file_path))

            # === DÃ‰BUT DU DOCUMENT HTML ===
            theme_bg = "#ffffff" if self.current_theme == "light" else "#2e2e2e"
            theme_color = "#000000" if self.current_theme == "light" else "#f0f0f0"

            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: sans-serif;
                        margin: 0;
                        padding: 20px;
                        max-width: none;
                        background-color: {theme_bg};
                        color: {theme_color};
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                        display: block;
                        margin: 20px auto;
                    }}
                    hr {{
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
            """

            # === COUVERTURE ===
            cover_item = self.get_epub_cover_image(book)
            if cover_item:
                cover_data = cover_item.get_content()
                encoded = base64.b64encode(cover_data).decode("utf-8")
                html_content += f"<img src='data:image/jpeg;base64,{encoded}' /><hr>"

            # === CONTENU HTML ===
            for item in book.get_items():
                if isinstance(item, epub.EpubHtml):
                    try:
                        html = item.get_content().decode("utf-8", errors="ignore")
                        html_content += html + "<hr>"
                    except Exception as e:
                        print(f"[WARN] Erreur sur l'item {item.file_name} : {e}")

            html_content += "</body></html>"

            # === AFFICHAGE VIA QWebEngineView ===
            if WEB_ENGINE_AVAILABLE:
                # Nettoyage de l'ancien fichier temporaire
                if hasattr(self, "current_epub_tmpfile"):
                    try:
                        os.unlink(self.current_epub_tmpfile)
                    except Exception as e:
                        print(f"[INFO] Impossible de supprimer l'ancien fichier temporaire : {e}")

                # Ã‰criture dans un fichier temporaire
                tmp = NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
                tmp.write(html_content)
                tmp.close()
                self.current_epub_tmpfile = tmp.name

                # Réutiliser l'instance unique html_preview
                if self.html_preview:
                    self._webview_load_url(QUrl.fromLocalFile(tmp.name))
                    self.preview_stack.setCurrentWidget(self.html_preview)

            else:
                self.show_text_preview(self.t("error_epub_preview_unavailable"))

        except Exception as e:
            self.show_text_preview(self.t("error_epub").format(error=str(e)))


    def get_epub_cover_image(self, book):
        try:
            from ebooklib import epub
            
            # Si book est un chemin relatif, il faut le résoudre
            if isinstance(book, str):  # Si book est une chaîne (chemin de fichier)
                book_path = config.FILES_DIR / book  # Résolution du chemin relatif
                book = epub.read_epub(str(book_path))  # Ouverture du fichier EPUB
            
            for item in book.get_items():
                # On vérifie si le mimetype correspond à une image
                if item.media_type.startswith("image/") and 'cover' in item.get_name().lower():
                    return item
            return None
        except Exception as e:
            print(f"[ERROR] Failed to extract cover image from EPUB: {e}")
            return None


    def show_docx_preview(self, file_path):
        try:
            import mammoth
            from tempfile import NamedTemporaryFile
            import os

            # Résoudre le chemin complet pour le fichier DOCX
            full_path = config.FILES_DIR / file_path  # Utiliser config.FILES_DIR ici

            print(f"[DEBUG] Lecture Word (Mammoth) : {full_path}")

            with open(win_path(full_path), "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value

            return f"<html><body style='font-family: sans-serif;'>{html}</body></html>"

        except Exception as e:
            print(f"[ERROR] DOCX to HTML failed: {e}")
            return None


    def show_xlsx_preview(self, file_path):
        try:
            # Résoudre le chemin complet pour le fichier XLSX ou XLSM
            full_path = config.FILES_DIR / file_path  # Utiliser config.FILES_DIR ici

            # Lire le fichier Excel (que ce soit .xlsx ou .xlsm)
            xls = pd.ExcelFile(win_path(full_path))  # Ouvre le fichier Excel

            # Clear the current tab widget
            self.xlsx_tab_widget.clear()

            for sheet_name in xls.sheet_names:  # Parcours toutes les feuilles
                df = pd.read_excel(xls, sheet_name=sheet_name)  # Lire la feuille dans un DataFrame

                # Créer un tableau QTableWidget pour afficher les données
                table = QTableWidget()
                table.setEditTriggers(QAbstractItemView.NoEditTriggers)
                table.setRowCount(df.shape[0])
                table.setColumnCount(df.shape[1])

                # Définir les en-têtes de colonnes AVANT de remplir les cellules
                table.setHorizontalHeaderLabels([
                    "" if str(col).startswith("Unnamed") else str(col)
                    for col in df.columns
                ])

                # Remplir les cellules
                for i, row in df.iterrows():
                    for j, value in enumerate(row):
                        display_value = "" if pd.isna(value) else str(value)
                        table.setItem(i, j, QTableWidgetItem(display_value))

                # Ajuster les dimensions des colonnes et des lignes
                table.resizeColumnsToContents()
                table.resizeRowsToContents()

                # Ajouter le tableau à l'onglet
                self.xlsx_tab_widget.addTab(table, sheet_name)

            # Masquer les autres prévisualisations et afficher le tableau Excel
            self.text_preview.hide()
            self.image_scroll.hide()
            self.zoom_controls_widget.hide()
            self.xlsx_tab_widget.setVisible(True)
            self.preview_stack.setCurrentWidget(self.xlsx_tab_widget)

        except Exception as e:
            print(f"[ERREUR] XLSX/XLSM multi-feuilles : {e}")
            self.show_text_preview(self.t("textfile_read_error").format(error=str(e)))

    def reset_search(self):
        # tout de suite, plus rien ne doit mettre à jour l'UI
        self._is_searching   = False
        self._search_aborted = False

        # Remise à zéro de l'UI
        self.search_input.clear()
        self.tree.clear()
        self.search_count_label.clear()
        self.search_count_label.hide()

        self.hide_progress_bar_fade()
        self.progress_label.clear()
        self.progress_label.hide()
        self.progress_bar.reset()
        self.progress_bar.hide()

        self.stop_search_button.setVisible(False)
        self.stop_search_button.setEnabled(True)

        self.load_documents()
        self.clear_preview()

        self.pdf_doc = None
        self.original_pixmap = None
        self.current_zoom = 1.0
        self.current_pdf_page = 0

        self.set_metadata_fields_enabled(False)
        self.toggle_metadata_button.setChecked(False)
        self.metadata_form.hide()

        # Désactive le bouton reset jusqu'à la prochaine recherche
        self.reset_button.setEnabled(False)



    def clear_preview(self):
        self.pdf_doc = None
        self.original_pixmap = None
        self.current_zoom = 1.0

        # Vider les prévisualisations de texte et les masquer
        if self.text_preview:
            self.text_preview.clear()
            self.text_preview.setVisible(False)

        # Vider la prévisualisation d'image et la masquer
        if self.image_preview_label:
            self.image_preview_label.clear()
            self.image_scroll.setVisible(False)

        # Nettoyer le QWebEngineView s'il existe, sans le supprimer
        if hasattr(self, 'html_preview') and self.html_preview is not None:
            try:
                self.html_preview.setHtml("")  # Efface le contenu HTML
                self.html_preview.hide()       # Masque le widget
            except RuntimeError as e:
                print(f"[AVERTISSEMENT] html_preview inaccessible : {e}")

        # Masquer les contrôles de zoom et les boutons de navigation
        self.zoom_controls_widget.hide()
        self.prev_page_button.hide()
        self.next_page_button.hide()
        self.top_page_selector.clear()
        self.top_page_selector.setVisible(False)
        self.top_selector_widget.setVisible(False)

        # Réinitialiser le bouton de métadonnées
        self.toggle_metadata_button.setEnabled(False)

        # Réinitialiser le widget XLSX
        if self.xlsx_tab_widget:
            self.xlsx_tab_widget.clear()
            self.xlsx_tab_widget.setVisible(False)

        # Réinitialiser le pied de page (nom du fichier)
        if hasattr(self, "file_info_label") and self.file_info_label:
            self.file_info_label.setText("")

        # Réinitialise les tags
        self.tag_filter_combo.setVisible(False)
        self.tag_filter_combo.setCurrentIndex(0)



    def delete_selected_items(self):
        selected_items = self.tree.selectedItems()
        print(f"[DEBUG] Nombre d'éléments sélectionnés : {len(selected_items)}")
        if not selected_items:
            QMessageBox.information(self, self.t("delete_confirm_title"), self.t("delete_nothing_selected"))
            return

        # Confirmation avant suppression
        _any_symlink = any(
            _is_symlink_robust(config.FILES_DIR / (i.data(0, Qt.ItemDataRole.UserRole) or ""))
            for i in selected_items if i.data(0, Qt.ItemDataRole.UserRole)
        )
        confirm = QMessageBox.question(
            self,
            self.t("delete_confirm_title"),
            self.t("delete_confirm_text_symlink") if _any_symlink else self.t("delete_confirm_text"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        with sqlite3.connect(config.DB_PATH) as conn:  
            cur = conn.cursor()

            for item in selected_items:
                rel_path = item.data(0, Qt.ItemDataRole.UserRole)
                print(f"[DEBUG] Donnée UserRole : {rel_path}")
                if not rel_path:
                    continue

                # Vérification verrou symlink
                if rel_path in self.locked_symlinks:
                    answer = QMessageBox.question(
                        self,
                        self.t("symlink_locked_title"),
                        self.t("symlink_locked_confirm_delete").format(name=Path(rel_path).name),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if answer != QMessageBox.Yes:
                        continue

                rel_path_str = str(rel_path).replace("\\", "/")
                full_path = config.FILES_DIR / rel_path  # Utiliser config.FILES_DIR pour obtenir le chemin complet

                print(f"[INFO] Suppression : {rel_path_str}")
                print(f"        Chemin absolu : {full_path}")
                print(f"        Type : {'Dossier' if full_path.is_dir() else 'Fichier'}")

                try:
                    if full_path.is_dir():
                        if _is_symlink_robust(full_path):  # lien (robuste Windows)
                            os.remove(win_path(full_path))  # win_path
                            print(f"        Lien symbolique supprimé")
                        else:
                            shutil.rmtree(win_path(full_path))  # win_path réels
                            print(f"        Dossier supprimé")

                        cur.execute("DELETE FROM documents WHERE path = ? OR path LIKE ?", (rel_path_str, rel_path_str + "/%"))
                        cur.execute("DELETE FROM document_metadata WHERE document_path = ? OR document_path LIKE ?", (rel_path_str, rel_path_str + "/%"))
                        print("        Enregistrements supprimés en base (documents + métadonnées)")

                    elif full_path.is_file():
                        os.remove(win_path(full_path))  # win_path
                        print(f"       Fichier supprimé")

                        cur.execute("DELETE FROM documents WHERE path = ?", (rel_path_str,))
                        cur.execute("DELETE FROM document_metadata WHERE document_path = ?", (rel_path_str,))
                        print("        Enregistrements supprimés en base (documents + métadonnées)")

                    else:
                        print("        Chemin introuvable")

                except Exception as e:
                    print(f"[ERREUR] Suppression échouée pour {rel_path_str} : {e}")
                    QMessageBox.warning(
                        self,
                        self.t("delete_error_title"),
                        self.t("delete_error_text").format(path=rel_path, error=str(e))
                    )

            conn.commit()

        print("[INFO] Suppression terminée")
        self.load_documents()
        self.update_file_count()
        self.reindex_files()
        self.clear_preview()

    def rename_selected_item(self):
        selected_items = self.tree.selectedItems()
        if not selected_items or len(selected_items) != 1:
            QMessageBox.information(self, self.t("rename_title"), self.t("rename_select_one"))
            return

        item = selected_items[0]
        rel_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not rel_path:
            return

        old_path = config.FILES_DIR / rel_path
        if not old_path.exists():
            QMessageBox.warning(self, self.t("rename_error_title"), self.t("file_not_found"))
            return

        # Garde verrou symlink
        if rel_path in self.locked_symlinks:
            answer = QMessageBox.question(
                self,
                self.t("symlink_locked_title"),
                self.t("symlink_locked_confirm_rename").format(name=Path(rel_path).name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                return

        old_name = old_path.name
        parent_path = old_path.parent

        new_name, ok = QInputDialog.getText(
            self,
            self.t("rename_title"),
            self.t("rename_prompt").format(old_name=old_name)
        )

        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        # Ajouter extension si oubliée (pour les fichiers uniquement)
        if old_path.is_file() and not os.path.splitext(new_name)[1]:
            new_name += old_path.suffix

        new_path = parent_path / new_name
        if new_path.exists():
            QMessageBox.warning(
                self,
                self.t("rename_error_title"),
                self.t("rename_already_exists").format(new_name=new_name)
            )
            return

        try:
            old_path.rename(new_path)
            rel_new_path = str(new_path.relative_to(config.FILES_DIR))

            # Mise à jour de la base SQLite
            with sqlite3.connect(config.DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE documents SET name = ?, path = ? WHERE path = ?", (
                    new_name,
                    rel_new_path,
                    rel_path
                ))
                cur.execute("UPDATE document_metadata SET document_path = ? WHERE document_path = ?", (
                    rel_new_path,
                    rel_path
                ))
                conn.commit()

            print(f"[OK] Renommé : {rel_path} â†’ {rel_new_path}")

            # Si le fichier renommé est affiché, mettre à jour la prévisualisation
            if self.file_info_label.text().strip() == str(rel_path):
                self.preview_document(rel_new_path)

            # Réindexation complète du dossier "files"
            print("[INFO] Réindexation après renommage...")
            self.reindex_files()  # Appelle ta fonction de réindexation
            self.load_documents()
            self.update_file_count()

        except Exception as e:
            QMessageBox.critical(
                self,
                self.t("rename_error_title"),
                self.t("rename_error_message").format(error=str(e))
            )



    def show_ged_statistics(self):
        stats = Counter()
        total_size = 0
        folder_count = 0
        stats["odt"] = 0
        stats["docx"] = 0
        stats["xlsx"] = 0
        stats["pptx"] = 0
        stats["ods"] = 0
        stats["odp"] = 0

        with sqlite3.connect(config.DB_PATH) as conn:  
            cur = conn.cursor()
            cur.execute("SELECT path, extension FROM documents WHERE extension != '.json'")
            for path, ext in cur.fetchall():
                ext = ext.lower()
                if ext == ".pdf":
                    stats["pdf"] += 1
                elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"]:
                    stats["images"] += 1
                elif ext in [".txt", ".md", ".py"]:
                    stats["textes"] += 1
                elif ext in [".html", ".htm"]:
                    stats["html"] += 1
                elif ext == ".docx":
                    stats["docx"] += 1
                elif ext == ".odt":
                    stats["odt"] += 1
                elif ext == ".ods":
                    stats["ods"] += 1
                elif ext == ".odp":
                    stats["odp"] += 1
                elif ext == ".xlsx":
                    stats["xlsx"] += 1
                elif ext == ".pptx":
                    stats["pptx"] += 1

                else:
                    stats["autres"] += 1

                try:
                    full_path = config.FILES_DIR / path  # Utilisation de config.FILES_DIR pour le chemin complet
                    if full_path.exists() and full_path.is_file():
                        total_size += full_path.stat().st_size
                except:
                    pass

        for root, dirs, _ in os.walk(config.FILES_DIR):  # Utilisation de config.FILES_DIR ici aussi
            folder_count += len(dirs)

        total_files = sum(stats.values())
        size_readable = humanize.naturalsize(total_size, binary=True)

        # === Boîte personnalisée ===
        dlg = QDialog(self)
        dlg.setWindowTitle(self.t("stats_title"))
        layout = QVBoxLayout(dlg)

        icon_map = {
            self.t("stats_total_files"): qta.icon("fa5s.copy", color="#007BFF"),
            self.t("stats_pdf"): qta.icon("fa5s.file-pdf", color="#007BFF"),
            self.t("stats_odt"): qta.icon("fa5s.file-word", color="#007BFF"),
            self.t("stats_ods"): qta.icon("fa5s.file-excel", color="#007BFF"),
            self.t("stats_odp"): qta.icon("fa5s.file-powerpoint", color="#007BFF"),
            self.t("stats_images"): qta.icon("fa5s.image", color="#007BFF"),
            self.t("stats_texts"): qta.icon("fa5s.file-alt", color="#007BFF"),
            self.t("stats_docx"): qta.icon("fa5s.file-word", color="#007BFF"),
            self.t("stats_xlsx"): qta.icon("fa5s.file-excel", color="#007BFF"),
            self.t("stats_pptx"): qta.icon("fa5s.file-powerpoint", color="#007BFF"),
            self.t("stats_html"): qta.icon("fa5s.code", color="#007BFF"),
            self.t("stats_other"): qta.icon("fa5s.question-circle", color="#007BFF"),
            self.t("stats_folders"): qta.icon("fa5s.folder", color="#007BFF"),
            self.t("stats_size"): qta.icon("fa5s.hdd", color="#007BFF"),
        }

        rows = [
            (self.t("stats_total_files"), total_files),
            (self.t("stats_pdf"), stats["pdf"]),
            (self.t("stats_images"), stats["images"]),
            (self.t("stats_texts"), stats["textes"]),
            (self.t("stats_odt"), stats["odt"]),
            (self.t("stats_docx"), stats["docx"]),
            (self.t("stats_xlsx"), stats["xlsx"]),
            (self.t("stats_pptx"), stats["pptx"]),
            (self.t("stats_html"), stats["html"]),
            (self.t("stats_other"), stats["autres"]),
            (self.t("stats_folders"), folder_count),
            (self.t("stats_size"), size_readable),
        ]

        stats_grid = QGridLayout()
        for i, (label, value) in enumerate(rows):
            icon_label = QLabel()
            icon_label.setPixmap(icon_map[label].pixmap(24, 24))
            stats_grid.addWidget(icon_label, i, 0)

            text_label = QLabel(f"{label} :")
            stats_grid.addWidget(text_label, i, 1)

            value_label = QLabel(str(value))
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            stats_grid.addWidget(value_label, i, 2)

        layout.addLayout(stats_grid)

        # === Boutons avec style rond ===
        btn_style = get_round_button_style()

        export_btn = QPushButton()
        export_btn.setIcon(qta.icon("fa5s.file-export", color="#007BFF"))
        export_btn.setToolTip(self.t("tooltip_export_stats"))
        export_btn.setFixedSize(40, 40)
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(lambda: self.export_ged_statistics(stats, folder_count, total_size))

        chart_btn = QPushButton()
        chart_btn.setIcon(qta.icon("fa5s.chart-pie", color="#007BFF"))
        chart_btn.setToolTip(self.t("tooltip_show_pie"))
        chart_btn.setFixedSize(40, 40)
        chart_btn.setStyleSheet(btn_style)
        chart_btn.clicked.connect(lambda: self.show_pie_chart(stats))

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times-circle", color="red"))
        close_btn.setToolTip(self.t("tooltip_close"))
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(dlg.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(chart_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        dlg.exec()


    def export_ged_statistics(self, stats, folder_count, total_size):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        import csv
        import humanize
        from PySide6.QtWidgets import QFileDialog

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("export_dialog_title"),
            "",
            "PDF (*.pdf);;CSV (*.csv)"
        )
        if not save_path:
            return

        total_files = sum(stats.values())
        size_readable = humanize.naturalsize(total_size, binary=True)

        data = [
            ("Fichiers totaux", total_files),
            ("PDF", stats["pdf"]),
            ("Images", stats["images"]),
            ("Textes", stats["textes"]),
            ("HTML", stats["html"]),
            ("Autres", stats["autres"]),
            ("Dossiers", folder_count),
            ("Taille totale", size_readable)
        ]

        if save_path.endswith(".csv"):
            with open(save_path, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([self.t("export_column_category"), self.t("export_column_value")])
                for row in data:
                    writer.writerow(row)

        elif save_path.endswith(".pdf"):
            c = canvas.Canvas(save_path, pagesize=A4)
            width, height = A4
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 50, self.t("export_pdf_title"))
            y = height - 100
            for key, val in data:
                c.drawString(60, y, f"{key} : {val}")
                y -= 20
            c.save()

        QMessageBox.information(
            self,
            self.t("export_success_title"),
            self.t("export_success_message").format(path=save_path)
        )

    def show_pie_chart(self, stats):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton

        # Préparer les données
        labels = []
        sizes = []
        for key, label_key in [
            ("pdf", "stats_pdf"),
            ("images", "stats_images"),
            ("textes", "stats_texts"),
            ("html", "stats_html"),
            ("autres", "stats_other")
        ]:
            count = stats[key]
            if count > 0:
                labels.append(self.t(label_key))
                sizes.append(count)

        if not sizes:
            QMessageBox.information(
                self,
                self.t("chart_no_data_title"),
                self.t("chart_no_data_message")
            )
            return

        # Créer une figure matplotlib
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')
        
        # Emballer la figure dans un widget Qt
        canvas = FigureCanvas(fig)

        # Créer une fenêtre Qt personnalisée
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("chart_window_title"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(canvas)

        close_btn = QPushButton(self.t("chart_close_button"))
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def show_backup_menu(self):
        menu = QMenu(self)

        action_backup = QAction(self.t("menu_backup_now"), self)
        action_restore = QAction(self.t("menu_restore_backup"), self)

        action_backup.triggered.connect(self.backup_ged)
        action_restore.triggered.connect(self.restore_ged)

        menu.addAction(action_backup)
        menu.addAction(action_restore)

        menu.exec(self.backup_button.mapToGlobal(self.backup_button.rect().bottomLeft()))

    
    def backup_ged(self):
        from PySide6.QtWidgets import QFileDialog, QProgressDialog
        from datetime import datetime
        default_name = f"ged_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        # Demander à l'utilisateur oÃ¹ sauvegarder le fichier
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("backup_dialog_title"),
            default_name,
            "Fichier ZIP (*.zip)"
        )

        if not save_path:
            return

        self.progress_dialog = QProgressDialog(
            self.t("backup_progress_text"),
            self.t("backup_cancel_button"),
            0, 100, self
        )
        self.progress_dialog.setWindowTitle(self.t("backup_window_title"))

        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        # Récupérer les traductions et la langue courante
        translations = self.translations
        current_language = self.current_language

        self.thread = QThread()
        self.backup_worker = BackupWorker(
            config.FILES_DIR, config.DB_PATH, save_path,
            translations, current_language
        )
        self.backup_worker.moveToThread(self.thread)

        # Connexion des signaux
        self.thread.started.connect(self.backup_worker.run)
        self.backup_worker.progress.connect(self.progress_dialog.setValue)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.error.connect(self.on_backup_error)

        # Nettoyage
        self.backup_worker.finished.connect(self.thread.quit)
        self.backup_worker.error.connect(self.thread.quit)
        self.backup_worker.finished.connect(self.backup_worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Important : attendre la fin réelle du thread pour éviter les fuites
        self.thread.finished.connect(lambda: self.thread.wait())

        # Démarrer
        self.thread.start()

    def on_backup_finished(self, message):
        self.progress_dialog.setValue(100)
        QMessageBox.information(self, self.t("backup_success_title"), message)

    def on_backup_error(self, error_message):
        self.progress_dialog.cancel()
        QMessageBox.critical(
            self,
            self.t("backup_error_title"),
            self.t("backup_error_message").format(error=error_message)
        )

    def restore_ged(self):
        from PySide6.QtWidgets import QFileDialog, QProgressDialog
        import zipfile
        import tempfile

        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("restore_dialog_title"),
            "",
            "Fichier ZIP (*.zip)"
        )

        if not zip_path:
            return

        reply = QMessageBox.question(
            self,
            self.t("restore_confirm_title"),
            self.t("restore_confirm_text"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # === Jauge de progression ===
        self.progress_dialog = QProgressDialog(
            self.t("restore_progress_text"),
            self.t("restore_cancel_button"),
            0, 100, self
        )
        self.progress_dialog.setWindowTitle(self.t("restore_window_title"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        # === Lancement du thread de restauration ===
        self.thread = QThread()
        self.restore_worker = RestoreWorker(zip_path, config.FILES_DIR, config.DB_PATH, self.translations, self.current_language)
        self.restore_worker.moveToThread(self.thread)

        self.thread.started.connect(self.restore_worker.run)
        self.restore_worker.progress.connect(self.progress_dialog.setValue)
        self.restore_worker.finished.connect(self.on_restore_finished)
        self.restore_worker.error.connect(self.on_restore_error)

        self.restore_worker.finished.connect(self.thread.quit)
        self.restore_worker.error.connect(self.thread.quit)
        self.restore_worker.finished.connect(self.restore_worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.finished.connect(lambda: self.thread.wait())
        self.thread.start()

    def on_restore_finished(self, message):
        self.progress_dialog.setValue(100)
        self.load_documents()
        self.update_file_count()
        self.clear_preview()
        self.reindex_files()
        QMessageBox.information(self, self.t("restore_done_title"), message)

    def on_restore_error(self, error_message):
        self.progress_dialog.cancel()
        QMessageBox.critical(
            self,
            self.t("restore_error_title"),
            self.t("restore_error_message").format(error=error_message)
        )

    def load_translations(self):
        """Charge les traductions depuis un fichier JSON."""
        try:
            # Utiliser le chemin centralisé de config.py pour les traductions
            with open(config.LANGUAGES_PATH, "r", encoding="utf-8") as file:
                self.translations = json.load(file)
            print("[DEBUG] Traductions chargées avec succès.")
        except Exception as e:
            print(f"[ERROR] Failed to load translations: {e}")
            self.translations = {}



    def change_language(self, lang_code):
        """Change la langue de l'application."""
        self.current_language = lang_code
        config.save_user_language(lang_code)
        self.load_translations()  # Recharge les traductions après avoir sauvegardé la langue
        self.update_language()  # Met à jour l'interface utilisateur
        self.update_window_title()



    def update_language(self):
        trans = self.translations.get(self.current_language, {})

        # Fenêtre à propos
        if hasattr(self, 'about_label'):
            cwd = os.getcwd()
            about_html = trans.get("about_full_text", "").format(cwd=cwd)
            self.about_label.setText(about_html)

        if hasattr(self, 'close_button'):
            self.close_button.setText(trans.get("close", "Fermer"))

        # TOOLTIP & PLACEHOLDER ZONE DE RECHERCHE
        if hasattr(self, 'search_input'):
            self.search_input.setPlaceholderText(self.t("search_placeholder"))
        if hasattr(self, 'search_button'):
            self.search_button.setToolTip(self.t("search_tooltip"))

        # TOOLTIP BOUTONS PRINCIPAUX
        if hasattr(self, 'reindex_button'):
            self.reindex_button.setToolTip(self.t("tooltip_reindex"))
        if hasattr(self, 'import_button'):
            self.import_button.setToolTip(self.t("tooltip_import"))
        if hasattr(self, 'reset_button'):
            self.reset_button.setToolTip(self.t("tooltip_reset"))
        if hasattr(self, 'info_button'):
            self.info_button.setToolTip(self.t("tooltip_about"))
        if hasattr(self, 'theme_button'):
            self.theme_button.setToolTip(self.t("tooltip_theme"))
        if hasattr(self, 'toggle_metadata_button'):
            self.toggle_metadata_button.setText(f" {self.t('button_metadata')}")
        if hasattr(self, 'label_author'):
            self.label_author.setText(self.t("label_author"))
        if hasattr(self, 'label_comment'):
            self.label_comment.setText(self.t("label_comment"))
        if hasattr(self, 'label_version'):
            self.label_version.setText(self.t("label_version"))
        if hasattr(self, 'label_updated'):
            self.label_updated.setText(self.t("label_updated"))
        if hasattr(self, 'save_metadata_button'):
            self.save_metadata_button.setText(self.t("button_save_metadata"))
        if hasattr(self, 'delete_button'):
            self.delete_button.setToolTip(self.t("tooltip_delete"))
        if hasattr(self, 'rename_button'):
            self.rename_button.setToolTip(self.t("tooltip_rename"))
        if hasattr(self, 'stats_button'):
            self.stats_button.setToolTip(self.t("tooltip_stats"))
        if hasattr(self, 'backup_button'):
            self.backup_button.setToolTip(self.t("tooltip_backup"))
        if hasattr(self, 'quit_button'):
            self.quit_button.setToolTip(self.t("tooltip_quit"))
        if hasattr(self, 'update_file_count'):
            self.update_file_count()
        if hasattr(self, 'export_btn'):
            self.export_btn.setToolTip(self.t("tooltip_export_stats"))
        if hasattr(self, 'label_tags'):
            self.label_tags.setText(self.t("label_tags"))
        if hasattr(self, 'meta_tag_open_btn'):
            pass  # libellé fixe, pas de clé de traduction nécessaire
        # Mise à jour de la barre de zoom avec traduction
        if hasattr(self, "zoom_label") and hasattr(self, "pdf_doc") and self.pdf_doc:
            label = self.t("zoom_with_page").format(
                percent=int(self.current_zoom * 100),
                current=self.current_pdf_page + 1,
                total=self.pdf_doc.page_count
            )
            self.zoom_label.setText(label)
        # Bouton de recherche dans les tags
        if hasattr(self, 'tag_filter_combo'):
            self.tag_filter_combo.setPlaceholderText(self.t("select_tag_filter"))
            self.tag_filter_button.setToolTip(self.t("filter_by_tag"))

    
    def _launch_scan_to_folder(self):
        """
        Lance l'application de numérisation système et propose de
        placer le fichier numérisé dans un dossier de la GED.
        """
        import subprocess, sys, shutil
        from pathlib import Path

        # Choisir le dossier de destination dans la GED
        dest_dir_str = QFileDialog.getExistingDirectory(
            self,
            self.t("scan_choose_dest_folder"),
            str(config.FILES_DIR),
            options=_file_dialog_options()
        )
        if not dest_dir_str:
            return
        dest_dir = Path(dest_dir_str)

        # Vérifier que la destination est dans la GED
        try:
            dest_dir.relative_to(config.FILES_DIR)
        except ValueError:
            QMessageBox.warning(self, self.t("error_title"), self.t("error_not_inside_ged"))
            return

        # Lancer le scanner système
        launched = False
        try:
            if sys.platform.startswith("win"):
                import os
                os.system("start wiaacmgr")
                launched = True
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", "-a", "Image Capture"])
                launched = True
            else:
                from database.path_utils import _clean_env_for_subprocess
                env = _clean_env_for_subprocess()
                for app in ["simple-scan", "xsane", "gscan2pdf", "skanlite"]:
                    if shutil.which(app):
                        subprocess.Popen([app], env=env)
                        launched = True
                        break
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"), str(e))
            return

        if not launched:
            QMessageBox.information(
                self,
                self.t("import_scan_document"),
                self.t("scan_no_app_found") if "scan_no_app_found" in
                self.translations.get(self.current_language, {})
                else "Aucun logiciel de numérisation trouvé.\nInstallez simple-scan, XSane ou gscan2pdf."
            )
            return

        # Inviter l'utilisateur à sélectionner le fichier numérisé une fois prêt
        QMessageBox.information(
            self,
            self.t("import_scan_document"),
            self.t("scan_ready_message") if "scan_ready_message" in
            self.translations.get(self.current_language, {})
            else "Une fois la numérisation terminée, sélectionnez le fichier obtenu."
        )

        scanned_file, _ = QFileDialog.getOpenFileName(
            self,
            self.t("scan_select_file"),
            str(Path.home()),
            "Images et PDF (*.pdf *.png *.jpg *.tif *.tiff *.bmp);;Tous les fichiers (*)",
            options=_file_dialog_options()
        )
        if not scanned_file:
            return

        src  = Path(scanned_file)
        dest = dest_dir / src.name
        if dest.exists():
            reply = QMessageBox.question(
                self,
                self.t("file_exists_title"),
                self.t("file_exists_message").format(name=src.name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        import shutil as _shutil
        _shutil.copy2(str(src), str(dest))
        self.folder_to_select_after_reindex = str(dest_dir.relative_to(config.FILES_DIR))
        self.reindex_files()
        QMessageBox.information(
            self,
            self.t("import_success_title"),
            self.t("import_success_file").format(name=src.name)
        )

    
    def show_about_window(self):
        # Créer un QWidget personnalisé (au lieu de QMessageBox)
        about_window = QDialog(self)
        about_window.setWindowTitle(self.t("about_title")) # Traduction du titre

        # Créer le layout principal
        main_layout = QVBoxLayout(about_window)

        # Créer une zone de défilement pour le texte
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Permet au contenu de se redimensionner
        main_layout.addWidget(scroll_area)

        # Créer un QWebEngineView LOCAL pour afficher le contenu HTML
        # NE PAS utiliser self.html_preview ici — cela écraserait le widget de prévisualisation principal
        about_web_view = QWebEngineView()
        scroll_area.setWidget(about_web_view)

        # Texte principal de la boîte "à propos"
        cwd = os.getcwd()
        about_html = self.translations.get(self.current_language, {}).get("about_full_text", "").format(cwd=cwd)

        # Charger le contenu HTML dans le QWebEngineView local
        about_web_view.setHtml(about_html)

        # Boutons de langue
        self.add_language_buttons(main_layout)

        # Bouton de fermeture
        self.close_button = QPushButton(self.t("close"))
        self.close_button.clicked.connect(about_window.close)
        main_layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Gestion du chemin pour la documentation "info.html"
        try:
            # Si l'application est compilée, chercher dans _MEIPASS
            if hasattr(sys, '_MEIPASS'):  # Si l'application est compilée
                info_path = Path(sys._MEIPASS) / 'assets' / 'info.html'
            else:
                info_path = config.ASSETS_DIR / 'info.html'

            # Vérifier si le fichier existe
            if info_path.exists():
                with open(info_path, 'r', encoding='utf-8') as file:
                    info_html = file.read()
                    about_web_view.setHtml(info_html)  # Afficher le contenu de info.html dans la fenêtre "à propos"
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de trouver la documentation.")
                return

        except Exception as e:
            print(f"[ERROR] Error loading info.html: {e}")
            about_web_view.setHtml(self.t("error_loading_info"))  # Message d'erreur

        # === Définir la taille minimale de la fenêtre ===
        about_window.setMinimumSize(600, 400)  # Par exemple, 600x400 pixels pour la fenêtre

        # ajuster la taille automatique selon le contenu
        about_window.resize(600, 400)  # définir une taille de départ

        # Affichage
        about_window.exec()



    def add_language_buttons(self, main_layout):
        # Récupérer le style des boutons de langue depuis le fichier de styles
        language_button_style = get_language_button_style()

        def make_flag_button(code, tooltip):
            btn = QPushButton()
            #flag_path = Path(resource_path(f"assets/flags/{code}.png"))
            flag_path = config.ASSETS_DIR / "flags" / f"{code}.png"
            btn.setIcon(QIcon(QPixmap(str(flag_path))))
            btn.setStyleSheet(language_button_style)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda: self.change_language(code))
            self.apply_hover_effect(btn)
            return btn

        # Création des boutons avec leurs codes de langue et labels
        buttons = {
            'fr': "Français",
            'en': "English",
            'de': "Deutsch",
            'it': "Italiano",
            'es': "Español",
            'nl': "Nederlands",
            'pt': "Português",
            'pl': "Polski",
            'sw': "Svenska",      # Swedish
            'dk': "Dansk",        # Danish
            'fi': "Suomi",        # Finnish
            'gr': "Ελληνικά",     # Greek
            'cz': "Čeština"       # Czech
        }

        language_layout = QHBoxLayout()
        for code, label in buttons.items():
            btn = make_flag_button(code, label)
            setattr(self, f"{code}_button", btn)
            language_layout.addWidget(btn)

        language_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(language_layout)


    
    def eventFilter(self, obj, event):
        # ── Ctrl+Molette : zoom image et WebEngine ────────────────────────────
        if event.type() == QEvent.Wheel:
            mods = event.modifiers()
            if mods & Qt.ControlModifier:
                delta = event.angleDelta().y()
                # Zoom image (image_scroll viewport)
                if hasattr(self, "image_scroll") and obj is self.image_scroll.viewport():
                    if delta > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    return True
                # Zoom WebEngine (QWebEngineView)
                if WEB_ENGINE_AVAILABLE and QWebEngineView and isinstance(obj.parent() if hasattr(obj, 'parent') else None, QWebEngineView):
                    pass  # géré nativement par QWebEngineView
                # Zoom PDF
                if hasattr(self, "image_scroll") and obj is self.image_scroll.viewport():
                    if delta > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    return True

        # ── Opacité animée du bouton accordéon sidebar ────────────────────────
        if hasattr(self, "_sidebar_btn") and obj is self._sidebar_btn:
            if hasattr(self, "_sidebar_btn_effect"):
                if event.type() == QEvent.Enter:
                    self._animate_sidebar_btn_opacity(1.0)
                elif event.type() == QEvent.Leave:
                    self._animate_sidebar_btn_opacity(0.32)
        if isinstance(obj, QPushButton) and obj is not getattr(self, "_sidebar_btn", None):
            if event.type() == QEvent.Enter:
                obj.setIconSize(QSize(42, 42))
            elif event.type() == QEvent.Leave:
                obj.setIconSize(QSize(32, 32))
        return super().eventFilter(obj, event)

    def _animate_sidebar_btn_opacity(self, target: float):
        from PySide6.QtCore import QVariantAnimation
        if hasattr(self, "_sidebar_opacity_anim") and \
                self._sidebar_opacity_anim.state() == QVariantAnimation.Running:
            self._sidebar_opacity_anim.stop()
        anim = QVariantAnimation(self)
        anim.setDuration(150)
        current = self._sidebar_btn_effect.opacity() if hasattr(self, "_sidebar_btn_effect") else 0.32
        anim.setStartValue(float(current))
        anim.setEndValue(float(target))
        anim.valueChanged.connect(
            lambda v: self._sidebar_btn_effect.setOpacity(v)
            if hasattr(self, "_sidebar_btn_effect") else None
        )
        anim.start()
        self._sidebar_opacity_anim = anim
        
    def apply_hover_effect(self, button: QPushButton):
        button.setIconSize(QSize(32, 32))
        button.installEventFilter(self)


    def render_current_pdf_page(self, dpi=150, adapt_to_width=False):
        if not self.pdf_doc or self.pdf_doc.page_count == 0:
            self.show_text_preview(self.t("pdf_empty_or_invalid"))
            return

        try:
            page = self.pdf_doc.load_page(self.current_pdf_page)
            pix = page.get_pixmap(dpi=dpi)
            mode = QImage.Format_RGB888 if pix.alpha == 0 else QImage.Format_RGBA8888
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, mode)
            pixmap = QPixmap.fromImage(img)

            if pixmap.isNull():
                self.show_text_preview(self.t("error_invalid_image"))
                return

            self.original_pixmap = pixmap
            self.preview_stack.setCurrentWidget(self.image_scroll)

            if adapt_to_width:
                viewport_width = self.image_scroll.viewport().width()
                ratio = viewport_width / pixmap.width()
                self.current_zoom = ratio  # stocker le zoom de départ
                self.update_zoom_label()

            self.apply_zoom()

            self.text_preview.hide()
            self.image_scroll.show()
            self.zoom_controls_widget.show()

            if self.pdf_doc.page_count > 1:
                self.prev_page_button.show()
                self.next_page_button.show()
            else:
                self.prev_page_button.hide()
                self.next_page_button.hide()

        except Exception as e:
            self.show_text_preview(self.t("pdf_render_error").format(error=e))

        if self.pdf_doc:
            label = self.t("zoom_with_page").format(
                percent=int(self.current_zoom * 100),
                current=self.current_pdf_page + 1,
                total=self.pdf_doc.page_count
            )
        else:
            label = f"{self.t('zoom')} {int(self.current_zoom * 100)}%"
        self.zoom_label.setText(label)

        if hasattr(self, "top_page_selector") and self.top_page_selector.isEnabled():
            self.top_page_selector.blockSignals(True)
            self.top_page_selector.setCurrentIndex(self.current_pdf_page)
            self.top_page_selector.blockSignals(False)




    def apply_zoom(self):
        if not self.original_pixmap:
            return

        # Taille cible en fonction du facteur de zoom
        scaled_pixmap = self.original_pixmap.scaled(
            self.original_pixmap.size() * self.current_zoom,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_preview_label.setPixmap(scaled_pixmap)
        self.image_preview_label.adjustSize()


    def show_image_preview(self, pixmap):
        self.preview_stack.setCurrentWidget(self.image_scroll)
        self.image_scroll.show()
        self.original_pixmap = pixmap

        viewport_width = self.image_scroll.viewport().width()
        if pixmap.width() == 0:
            self.show_text_preview(self.t("error_invalid_image_width"))
            return

        scale_ratio = viewport_width / pixmap.width()
        fitted_pixmap = pixmap.scaledToWidth(viewport_width, Qt.SmoothTransformation)

        self.image_preview_label.setPixmap(fitted_pixmap)
        self.image_preview_label.adjustSize()

        self.current_zoom = scale_ratio
        self.update_zoom_label()

        self.zoom_controls_widget.show()
        if self.pdf_doc and self.pdf_doc.page_count > 1:
            self.prev_page_button.show()
            self.next_page_button.show()
        else:
            self.prev_page_button.hide()
            self.next_page_button.hide()

        self.preview_stack.setCurrentWidget(self.image_scroll)

    def preview_textual_file(self, path: Path):
        ext = path.suffix.lower()
        try:
            if ext in [".txt", ".md", ".py"]:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                self.display_text_content(text)

            elif ext == ".epub":
                self.show_epub_preview(path)

            elif ext in [".docx"]:
                print(f"[DEBUG] Lecture Word (Mammoth) : {path}")
                try:
                    html = convert_docx_to_html(path)
                    full_html = f"<html><body style='font-family:sans-serif;padding:20px'>{html}</body></html>"

                    from tempfile import NamedTemporaryFile
                    tmp = NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
                    tmp.write(full_html)
                    tmp.close()

                    if WEB_ENGINE_AVAILABLE and self.html_preview:
                        # même logique que pour EPUB : supprimer ancien fichier et recréer html_preview
                        self._webview_load_url(QUrl.fromLocalFile(tmp.name))
                        self.show_preview_widget(self.html_preview)
                    else:
                        self.show_text_preview(self.t("disabled_html_preview"))

                except Exception as e:
                    self.show_text_preview(self.t("error_docx_mammoth").format(error=str(e)))

            else:
                self.display_text_content(self.t("unsupported_text_type"))

        except Exception as e:
            self.display_text_content(self.t("textfile_read_error").format(error=str(e)))

    def display_text_content(self, text: str):
        self.clear_preview()
        self.text_preview.setPlainText(text)
        self.text_preview.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  
        #self.text_preview.setAlignment(Qt.AlignTop)
        self.text_preview.setVisible(True)
        self.preview_stack.setCurrentWidget(self.text_preview)

    def show_text_preview(self, text):
        self.clear_preview()
        self.text_preview.setPlainText(text)
        self.text_preview.setVisible(True)
        self.preview_stack.setCurrentWidget(self.text_preview)
    
    def rotate_image(self):
        if hasattr(self, 'current_image'):
            try:
                # Tourner l'image de 90 degrés
                rotated_image = self.current_image.rotate(90, expand=True)
                self.current_image = rotated_image  # Mettre à jour l'image avec la version tournée

                # Convertir l'image Pillow en QPixmap
                qim = ImageQt(rotated_image)  # Convertir l'image Pillow en QImage
                pixmap = QPixmap.fromImage(qim)  # Convertir QImage en QPixmap

                # Réafficher l'image après rotation
                self.show_image_preview(pixmap)  # Utiliser un QPixmap pour l'affichage
            except Exception as e:
                print(f"[ERREUR] Erreur lors de la rotation de l'image : {e}")
        else:
            print("[ERREUR] Aucune image à faire pivoter.")

    def zoom_in(self):
        # Zoom SVG via QWebEngineView
        if hasattr(self, 'svg_web_view') and self.svg_web_view and \
                self.preview_stack.currentWidget() is self.svg_web_view:
            factor = self.svg_web_view.zoomFactor()
            self.svg_web_view.setZoomFactor(min(factor + 0.15, 5.0))
            self.zoom_label.setText(f"{self.t('zoom')}{int(self.svg_web_view.zoomFactor() * 100)}%")
            return
        self.current_zoom = min(self.current_zoom + 0.1, 5.0)
        self.update_zoom_label()
        self.update_pdf_zoom()

    def zoom_out(self):
        # Zoom SVG via QWebEngineView
        if hasattr(self, 'svg_web_view') and self.svg_web_view and \
                self.preview_stack.currentWidget() is self.svg_web_view:
            factor = self.svg_web_view.zoomFactor()
            self.svg_web_view.setZoomFactor(max(factor - 0.15, 0.2))
            self.zoom_label.setText(f"{self.t('zoom')}{int(self.svg_web_view.zoomFactor() * 100)}%")
            return
        self.current_zoom = max(0.2, self.current_zoom - 0.1)
        self.update_zoom_label()
        self.update_pdf_zoom()

    def update_zoom_label(self):
        if self.pdf_doc:
            self.zoom_label.setText(
                self.t("zoom_with_page").format(
                    percent=int(self.current_zoom * 100),
                    current=self.current_pdf_page + 1,
                    total=self.pdf_doc.page_count
                )
            )
        else:
            self.zoom_label.setText(
                f"{self.t('zoom')}{int(self.current_zoom * 100)}%"
            )


    def update_pdf_zoom(self):
        if self.pdf_doc:
            dpi = int(150 * self.current_zoom)
            dpi = max(72, min(dpi, 600))
            self.render_current_pdf_page(dpi)
        else:
            self.apply_zoom()

    def previous_pdf_page(self):
        if self.pdf_doc and self.current_pdf_page > 0:
            self.current_pdf_page -= 1
            self.render_current_pdf_page()

    def next_pdf_page(self):
        if self.pdf_doc and self.current_pdf_page < self.pdf_doc.page_count - 1:
            self.current_pdf_page += 1
            self.render_current_pdf_page()

    def eventFilter(self, source, event):
        try:
            scroll_vp = self.image_scroll.viewport()
        except RuntimeError:
            return super().eventFilter(source, event)
        if source is scroll_vp:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_start_pos = event.pos()
                source.setCursor(Qt.ClosedHandCursor)
                return True
            elif event.type() == QEvent.MouseMove and self._drag_start_pos:
                delta = self._drag_start_pos - event.pos()
                self.image_scroll.horizontalScrollBar().setValue(
                    self.image_scroll.horizontalScrollBar().value() + delta.x())
                self.image_scroll.verticalScrollBar().setValue(
                    self.image_scroll.verticalScrollBar().value() + delta.y())
                self._drag_start_pos = event.pos()
                return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._drag_start_pos = None
                source.setCursor(Qt.OpenHandCursor)
                return True
        return super().eventFilter(source, event)

    def load_image_file(self, image_path):
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.show_text_preview(self.t("error_image_load_failed"))
            return

        self.pdf_doc = None  # on s'assure qu'on n'est plus en mode PDF
        self.current_zoom = 1.0
        self.show_image_preview(pixmap)

    def display_epub(self, file_path):
        try:
            book = epub.read_epub(str(file_path))
            content = ""
            for item in book.get_items():
                if isinstance(item, epub.EpubHtml):  
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    content += soup.get_text() + "\n\n"

            if content.strip():
                self.text_preview.setPlainText(content)
            else:
                self.text_preview.setPlainText(self.t("epub_empty_or_unreadable"))

            self.text_preview.setVisible(True)

        except Exception as e:
            print(f"[ERREUR EPUB] {e}")
            self.text_preview.setPlainText(self.t("epub_open_error"))
            self.text_preview.setVisible(True)


    def _on_tree_item_moved(self, src_rel, new_rel):
        """Declenche par DraggableTreeWidget apres un deplacement interne."""
        self.reindex_files()

    def _on_tree_external_drop(self, paths: list, dest_rel: str, mode: str):
        """
        Gère un drag & drop depuis l'explorateur externe (Windows/Linux).
        mode = "copy" | "move"
        """
        import shutil
        dest_dir = config.FILES_DIR / dest_rel if dest_rel else config.FILES_DIR
        added = []
        errors = []
        for src in paths:
            src_path = Path(src)
            dest_path = dest_dir / src_path.name
            if dest_path.exists():
                reply = QMessageBox.question(
                    self,
                    self.t("file_exists_title"),
                    self.t("file_exists_message").format(name=src_path.name),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    continue
            try:
                if mode == "move":
                    shutil.move(str(src_path), str(dest_path))
                else:
                    if src_path.is_dir():
                        shutil.copytree(str(src_path), str(dest_path))
                    else:
                        shutil.copy2(str(src_path), str(dest_path))
                added.append(src_path.name)
            except Exception as e:
                errors.append(f"{src_path.name} : {e}")

        if errors:
            QMessageBox.warning(self, self.t("error_title"),
                                "\n".join(errors))
        if added:
            self.reindex_files()

    def reindex_files(self):
        class ReindexWorker(QObject):
            progress = Signal(int, int)
            finished = Signal(int)
            error = Signal(str)

            def run(self):
                try:
                    from database.reindex import reindex_files_with_progress
                    print("[DEBUG] Réindexation démarrée...")
                    count = reindex_files_with_progress(self.progress.emit)
                    print(f"[DEBUG] Réindexation terminée : {count} fichiers indexés.")
                    self.finished.emit(count)
                except Exception as e:
                    print("[ERREUR] Réindexation échouée :", e)
                    self.error.emit(str(e))

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.reindex_button.setEnabled(False)

        self.worker_thread = QThread()
        self.worker = ReindexWorker()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._update_progress_value)
        self.worker.finished.connect(self.on_reindex_done)
        self.worker.error.connect(self.on_reindex_error)

        # Quitter proprement
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)

        # Libérer les objets
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Attendre la fin réelle du thread
        self.worker_thread.finished.connect(lambda: self.worker_thread.wait())

        self.worker_thread.start()

    def import_external_file_or_folder(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        import shutil
        from pathlib import Path
        import os

        # 1) Choix du type d'import
        type_choice, ok = self._pick_item_dialog(
            self.t("import_type_title"),
            self.t("import_action_question"),
            [
                self.t("import_file"),
                self.t("import_folder"),
                self.t("create_new_folder"),
                self.t("import_scan_document"),
            ]
        )
        if not ok:
            return

        # 2) Numérisation d'un document
        if type_choice == self.t("import_scan_document"):
            self._launch_scan_to_folder()
            return

        # 3) Création d'un nouveau dossier si souhaité
        if type_choice == self.t("create_new_folder"):
            folder_name, ok = QInputDialog.getText(
                self,
                self.t("new_folder_title"),
                self.t("new_folder_question")
            )
            if ok and folder_name.strip():
                selected_item = self.tree.currentItem()
                if selected_item:
                    rel_path = selected_item.data(0, Qt.ItemDataRole.UserRole)
                    selected_path = config.FILES_DIR / rel_path
                    base_dir = selected_path if selected_path.is_dir() else selected_path.parent
                else:
                    base_dir = config.FILES_DIR

                new_path = base_dir / folder_name.strip()
                try:
                    new_path.mkdir(parents=True, exist_ok=False)
                    (new_path / ".keep").touch()
                    self.folder_to_select_after_reindex = str(new_path.relative_to(config.FILES_DIR))
                    self.reindex_files()
                    QMessageBox.information(
                        self,
                        self.t("folder_created_title"),
                        self.t("folder_created_message").format(name=folder_name)
                    )
                except FileExistsError:
                    QMessageBox.warning(
                        self,
                        self.t("folder_exists_title"),
                        self.t("folder_exists_message").format(name=folder_name)
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        self.t("folder_error_title"),
                        self.t("folder_error_message").format(error=str(e))
                    )
            return

        # 3) Choix du fichier ou dossier source
        if type_choice == self.t("import_file"):
            source_path, _ = QFileDialog.getOpenFileName(
                self, self.t("import_file_dialog"), "", "Tous les fichiers (*)",
                options=_file_dialog_options()
            )
        else:
            source_path = QFileDialog.getExistingDirectory(
                self, self.t("import_folder_dialog"),
                options=_file_dialog_options()
            )
        if not source_path:
            return

        file_path = Path(source_path)
        folder_name = file_path.name

        # 4) Choix du mode (copy ou link)
        options = {
            "copy": self.t("import_mode_copy"),    # ex: "Copier"
            "link": self.t("import_mode_link")     # ex: "Créer un lien symbolique"
        }
        reverse_options = {v: k for k, v in options.items()}
        selected_text, ok = self._pick_item_dialog(
            self.t("import_mode_title"),
            self.t("import_mode_question"),
            list(options.values())
        )
        if not ok:
            return
        mode = reverse_options[selected_text]

        # 5) NOUVEAU : choix du sous-dossier DESTINATION dans files/
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            self.t("select_target_folder"),
            str(config.FILES_DIR),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks | _file_dialog_options()
        )
        if not dest_dir:
            return
        dest_dir = Path(dest_dir)
        target = dest_dir / folder_name

        # 6) Copie / symlink + réindex
        try:
            if file_path.is_dir():
                if mode == "copy":
                    shutil.copytree(str(file_path), str(target))
                else:
                    try:
                        os.symlink(str(file_path), str(target), target_is_directory=True)
                    except (OSError, NotImplementedError):
                        shutil.copytree(str(file_path), str(target))
            else:
                if mode == "copy":
                    shutil.copy2(str(file_path), str(target))
                else:
                    try:
                        os.symlink(str(file_path), str(target), target_is_directory=False)
                    except (OSError, NotImplementedError):
                        shutil.copy2(str(file_path), str(target))

            # Met à jour le dossier à sélectionner après réindex
            self.folder_to_select_after_reindex = str(dest_dir.relative_to(config.FILES_DIR))
            self.reindex_files()

            # Message de succès
            msg_key = "import_success_folder" if file_path.is_dir() else "import_success_file"
            QMessageBox.information(
                self,
                self.t("import_success_title"),
                self.t(msg_key).format(name=folder_name)
            )

        except Exception as e:
            # En cas d'erreur, annule la barre de progression et affiche l'erreur
            self.hide_progress_bar_fade()
            QMessageBox.critical(
                self,
                self.t("import_error_title"),
                self.t("import_error_message").format(error=str(e))
            )


    def on_reindex_done(self, count):
        print(f"[INFO] Réindexation : {count} fichier(s) détecté(s)")

        # Important : déconnecte les signaux ici aussi
        try: self.worker.progress.disconnect()
        except: pass
        try: self.worker.finished.disconnect()
        except: pass

        try:
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(3000)
            self.worker.deleteLater()
            self.worker_thread.deleteLater()
        except Exception:
            pass
        self.worker = None
        self.worker_thread = None

        self.hide_progress_bar_fade()
        self.reindex_button.setEnabled(True)
        self.load_documents()
        self.clear_preview()

        # Sélectionner le dossier créé s'il a été stocké
        if hasattr(self, "folder_to_select_after_reindex"):
            self.select_and_expand_item(self.folder_to_select_after_reindex)
            del self.folder_to_select_after_reindex

        self.update_file_count()

        # Rafraîchir le folder_browser s'il affiche un dossier
        if hasattr(self, 'folder_browser') and self.folder_browser._current_path:
            fp = self.folder_browser._current_path
            if fp.exists():
                self.folder_browser.load_folder(fp, push_history=False)

        # Rafraîchir la prévisualisation si un fichier est toujours sélectionné
        current_item = self.tree.currentItem()
        if current_item:
            rel_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            if rel_path:
                self.load_preview_from_path(rel_path)

        msg_text = self.t("reindex_done_message").format(count=count)
        self.statusBar().showMessage(f"✅  {msg_text}", 5000)

    def on_reindex_error(self, error):
        try:
            self.worker.progress.disconnect()
            self.worker.error.disconnect()
        except:
            pass

        self.hide_progress_bar_fade()
        self.reindex_button.setEnabled(True)

        QMessageBox.critical(
            self,
            self.t("reindex_error_title"),
            self.t("reindex_error_message").format(error=error)
        )

    def select_and_expand_item(self, rel_path):
        parts = rel_path.split(os.sep)
        parent = None
        path_accumulator = []

        for i, part in enumerate(parts):
            path_accumulator.append(part)
            current_path = os.sep.join(path_accumulator)
            existing = self.find_tree_item(part, parent)

            if not existing:
                return  # l'élément n'a pas été trouvé

            parent = existing

            if i == len(parts) - 1:
                existing.setSelected(True)
                self.tree.scrollToItem(existing)
            else:
                existing.setExpanded(True)


    def on_tree_item_clicked(self, item, column):
        rel_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not rel_path:
            self.set_metadata_fields_enabled(False)
            self.metadata_form.hide()
            self.toggle_metadata_button.setEnabled(False)
            return

        full_path = config.FILES_DIR / rel_path

        if full_path.is_dir():
            # MODE EXPLORATEUR : afficher le contenu du dossier
            item.setExpanded(True)
            self._show_folder_browser(full_path)
            # Masquer métadonnées (non pertinent pour un dossier)
            self.set_metadata_fields_enabled(False)
            self.metadata_form.hide()
            self.toggle_metadata_button.setEnabled(False)
            return

        # MODE PRÉVISUALISATION (comportement inchangé) 
        self._exit_folder_browser()
        self.load_preview_from_path(rel_path)
        self.load_metadata(rel_path)
        self.toggle_metadata_button.setEnabled(True)
        # Surlignage automatique du terme de recherche en cours
        self._schedule_search_highlight()
    
    # Navigateur de dossiers 
    def _show_folder_browser(self, abs_path):
        """Bascule la zone centrale en mode explorateur de dossiers."""
        self.clear_preview()
        self.previewed_file_path = None
        self.folder_browser.load_folder(abs_path)
        self.preview_stack.setCurrentWidget(self.folder_browser)
        self.toggle_metadata_button.hide()
        self.zoom_controls_widget.hide()
        self.top_selector_widget.setVisible(False)
        self.file_info_label.setText(f"📂  {abs_path.name}")
        self.update_file_info_label_state(False)

    def _exit_folder_browser(self):
        """Quitte le mode explorateur (revient à la prévisualisation)."""
        self.toggle_metadata_button.show()

    def _on_folder_browser_file_clicked(self, rel_path: str):
        """
        Appelé quand l'utilisateur clique sur un fichier dans le navigateur.
        Bascule vers la prévisualisation du fichier.
        """
        self._exit_folder_browser()
        self.load_preview_from_path(rel_path)
        self.load_metadata(rel_path)
        self.toggle_metadata_button.setEnabled(True)

        # Sélectionner l'item correspondant dans le panneau gauche
        self._select_tree_item_by_rel_path(rel_path)

    def _on_folder_browser_navigated(self, abs_path_str: str):
        """
        Appelé quand le navigateur entre dans un sous-dossier.
        Synchronise la sélection dans le panneau gauche (arbre).
        """
        abs_path = Path(abs_path_str)
        try:
            rel = str(abs_path.relative_to(config.FILES_DIR))
        except ValueError:
            return
        self._select_tree_folder_by_rel_path(rel)
        self.file_info_label.setText(f"📂  {abs_path.name}")

    def _print_previewed_file(self):
        """Imprime le fichier actuellement prévisualisé."""
        if not self.previewed_file_path or not self.previewed_file_path.exists():
            return
        try:
            import subprocess, sys, shutil
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(self.previewed_file_path), "print")
            elif sys.platform.startswith("darwin"):
                result = subprocess.run(["lpr", str(self.previewed_file_path)],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    self._show_print_error(result.stderr)
            else:
                from database.path_utils import _clean_env_for_subprocess
                env = _clean_env_for_subprocess()
                check = subprocess.run(["lpstat", "-d"],
                                       capture_output=True, text=True, env=env)
                if ("no system default" in check.stdout.lower()
                        or "aucune destination" in check.stdout.lower()
                        or check.returncode != 0):
                    self._show_print_error(
                        self.t("print_no_default") if "print_no_default" in
                        self.translations.get(self.current_language, {})
                        else "Aucune imprimante par défaut configurée.\n\n"
                             "• Ouvrez les paramètres système → Imprimantes\n"
                             "• Ou : lpoptions -d <nom_imprimante>"
                    )
                    return
                result = subprocess.run(["lpr", str(self.previewed_file_path)],
                                        capture_output=True, text=True, env=env)
                if result.returncode != 0:
                    self._show_print_error(result.stderr or result.stdout)
        except FileNotFoundError:
            self._show_print_error("La commande 'lpr' est introuvable.\nInstallez CUPS : sudo apt install cups")
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"), f"Impossible d'imprimer : {e}")

    def _print_file(self, rel_path: str):
        """Imprime le fichier sélectionné dans le navigateur."""
        import subprocess, sys, shutil
        abs_path = config.FILES_DIR / rel_path
        if not abs_path.exists():
            return
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(abs_path), "print")

            elif sys.platform.startswith("darwin"):
                result = subprocess.run(["lpr", str(abs_path)],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    self._show_print_error(result.stderr)

            else:
                # Linux : vérifier qu'une imprimante par défaut existe
                from database.path_utils import _clean_env_for_subprocess
                env = _clean_env_for_subprocess()

                # lpstat -d donne l'imprimante par défaut
                check = subprocess.run(["lpstat", "-d"],
                                       capture_output=True, text=True, env=env)
                no_default = ("no system default destination" in check.stdout.lower()
                              or "aucune destination" in check.stdout.lower()
                              or check.returncode != 0)

                if no_default:
                    self._show_print_error(
                        self.t("print_no_default") if "print_no_default" in
                        self.translations.get(self.current_language, {})
                        else "Aucune imprimante par défaut configurée.\n\n"
                             "Pour configurer une imprimante :\n"
                             "• Ouvrez les paramètres système → Imprimantes\n"
                             "• Ou installez CUPS : sudo apt install cups\n"
                             "• Puis définissez une imprimante par défaut avec :\n"
                             "  lpoptions -d <nom_imprimante>"
                    )
                    return

                result = subprocess.run(["lpr", str(abs_path)],
                                        capture_output=True, text=True, env=env)
                if result.returncode != 0:
                    self._show_print_error(result.stderr or result.stdout)

        except FileNotFoundError:
            self._show_print_error(
                "La commande 'lpr' est introuvable.\n\n"
                "Installez CUPS : sudo apt install cups"
            )
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"),
                                f"Impossible d'imprimer : {e}")

    def _show_print_error(self, detail: str):
        """Affiche un message d'erreur d'impression clair."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(self.t("error_title"))
        msg.setText(detail.strip())
        msg.exec()

    def _select_tree_item_by_rel_path(self, rel_path: str):
        """Sélectionne dans l'arbre l'item correspondant au rel_path donné."""
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == rel_path:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                break
            iterator += 1

    def _select_tree_folder_by_rel_path(self, rel_path: str):
        """Sélectionne dans l'arbre le dossier correspondant au rel_path donné."""
        rel_path = rel_path.rstrip(os.sep)
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.rstrip(os.sep) == rel_path:
                self.tree.setCurrentItem(item)
                item.setExpanded(True)
                self.tree.scrollToItem(item)
                break
            iterator += 1

    # fin navigateur de dossiers 



    def load_preview_from_path(self, rel_path):
        self.clear_preview()  # Réinitialiser la zone de prévisualisation
        doc_path = config.FILES_DIR / rel_path
        self.previewed_file_path = doc_path
        self.update_file_info_label_state(True)

        # Afficher le chemin (tronque si trop long)
        _p = str(rel_path).replace("\\", "/")
        _p = ("..." + _p[-77:]) if len(_p) > 80 else _p
        self.file_info_label.setText("📄  " + _p)

        if not path_exists(doc_path):
            self.show_text_preview(self.t("error_file_not_found"))
            return

        # Afficher la barre de contrôles avec le bouton print pour tous les types
        self.zoom_controls_widget.show()

        ext = os.path.splitext(doc_path)[1].lower()

        try:
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"]:
                # C'est une image
                image = Image.open(win_path(doc_path))
                self.current_image = image  # Stocker l'image actuelle pour la rotation

                # Vérifier EXIF pour orientation et corriger
                try:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break
                    exif = dict(image._getexif().items())
                    orientation_value = exif.get(orientation, None)
                    if orientation_value == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation_value == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation_value == 8:
                        image = image.rotate(90, expand=True)
                except Exception as exif_err:
                    print(f"[INFO] Aucune orientation EXIF ou erreur : {exif_err}")

                # Convertir l'image Pillow en QPixmap
                qim = ImageQt(image)
                self.original_pixmap = QPixmap.fromImage(qim)  # Stocker l'image sous forme de QPixmap

                self.show_image_preview(self.original_pixmap)  # Afficher l'image en QPixmap

                # Afficher le bouton de rotation uniquement pour les images
                self.rotate_button.setVisible(True)  

            else:
                # Si ce n'est pas une image, on cache le bouton de rotation
                self.rotate_button.setVisible(False)

        except Exception as e:
            print(f"[ERREUR] Erreur de prévisualisation de l'image : {e}")
            self.show_text_preview(self.t("error_invalid_image"))

        try:
            # === HTML ===
            if ext in [".html", ".htm"]:
                if WEB_ENGINE_AVAILABLE and self.html_preview:
                    self._webview_load_url(QUrl.fromLocalFile(str(doc_path)))
                    self.preview_stack.setCurrentWidget(self.html_preview)
                else:
                    with open(win_path(doc_path), "r", encoding="utf-8", errors="ignore") as fhtml:
                        self.show_text_preview(fhtml.read())

            # === TEXTES ===
            elif ext in [".txt", ".py", ".epub", ".doc"]:
                self.preview_textual_file(doc_path)

            # === PDF ===
            elif ext == ".pdf":
                self.pdf_doc = fitz.open(win_path(doc_path))
                self.current_pdf_page = 0
                self.current_zoom = 1.0
                self.render_current_pdf_page(adapt_to_width=True)

                page_count = self.pdf_doc.page_count
                print(f"[DEBUG] PDF détecté avec {page_count} pages")

                if page_count > 1:
                    self.top_page_selector.blockSignals(True)
                    self.top_page_selector.clear()
                    for i in range(page_count):
                        icon = qta.icon("fa5.file-alt", color="#007BFF")  
                        self.top_page_selector.addItem(icon, f"{self.t('page')} {i + 1}")
                        #self.top_page_selector.addItem(f"Page {i + 1}")
                    self.top_page_selector.setCurrentIndex(0)
                    self.top_page_selector.setVisible(True)
                    self.top_page_selector.setEnabled(True)
                    self.top_page_selector.blockSignals(False)
                    self.top_selector_widget.setVisible(True)  
                else:
                    self.top_page_selector.clear()
                    self.top_page_selector.setVisible(False)
                    self.top_page_selector.setEnabled(False)
                    self.top_selector_widget.setVisible(False)  

            # === IMAGES ===
            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"]:
                try:
                    image = Image.open(win_path(doc_path))
                    try:
                        for orientation in ExifTags.TAGS.keys():
                            if ExifTags.TAGS[orientation] == 'Orientation':
                                break
                        exif = dict(image._getexif().items())
                        orientation_value = exif.get(orientation, None)
                        if orientation_value == 3:
                            image = image.rotate(180, expand=True)
                        elif orientation_value == 6:
                            image = image.rotate(270, expand=True)
                        elif orientation_value == 8:
                            image = image.rotate(90, expand=True)
                    except Exception as exif_err:
                        print(f"[INFO] Aucune orientation EXIF ou erreur : {exif_err}")

                    image = image.convert("RGBA")
                    data = image.tobytes("raw", "RGBA")
                    qim = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qim)

                    if pixmap.isNull():
                        self.show_text_preview(self.t("error_invalid_image"))
                    else:
                        self.pdf_doc = None
                        self.current_zoom = 1.0
                        self.show_image_preview(pixmap)
                except Exception as e:
                    QMessageBox.critical(self, self.t("error_loading_image_title"), str(e))

            # === DOCX ===
            elif ext == ".docx":
                html = self.show_docx_preview(doc_path)
                if html and WEB_ENGINE_AVAILABLE and self.html_preview:
                    self._webview_set_html(html)
                    self.preview_stack.setCurrentWidget(self.html_preview)
                else:
                    self.show_text_preview(self.t("docx_empty_or_webengine_unavailable"))
            
            # === XLSX ===
            elif ext in [".xlsx", ".xlsm"]:
                self.show_xlsx_preview(doc_path)

            # === PPTX ===
            elif ext == ".pptx":
                content = odf_utils.extract_text_from_pptx(doc_path)
                if content:
                    self.show_text_preview(content)
                else:
                    self.show_text_preview(self.t("textfile_read_error").format(error="PPTX vide ou invalide"))

            # === ODT ===
            elif ext == ".odt":
                html = odf_utils.odf_to_html(doc_path)
                if html and WEB_ENGINE_AVAILABLE and self.html_preview:
                    self._webview_set_html(html)
                    self.preview_stack.setCurrentWidget(self.html_preview)
                else:
                    self.show_text_preview(self.t("odt_empty_or_webengine_unavailable"))

            # === ODS / ODP ===
            elif ext == ".ods":
                self.show_ods_preview(rel_path)

            elif ext == ".odp":
                html = odf_utils.odp_to_html(doc_path)
                self.show_html_preview(html)
            
            # === MHTML ===
            elif ext in (".mhtml", ".mht"):
                self.show_mhtml_preview(doc_path)

            # === MARKDOWN ===
            elif ext == ".md":
                self._show_markdown_preview(doc_path)

            # === EML ===
            elif ext == ".eml":
                self.show_eml_preview(doc_path)

            # === XML ===
            elif ext == ".xml":
                self.show_xml_preview(rel_path)

            # === SVG ===
            elif ext == ".svg":
                self.show_svg_preview(rel_path)

            else:
                self._show_unsupported_file(doc_path)

        except Exception as e:
            QMessageBox.critical(self, self.t("error_reading_file"), str(e))

    # ------------------------------------------------------------------
    # Fichier non supporté nativement
    # ------------------------------------------------------------------
    def _show_unsupported_file(self, doc_path: Path):
        """
        Affiche un écran 'type non pris en charge' avec bouton pour ouvrir
        dans l'application par défaut ou une application configurée dans externe.cfg.
        """
        from styles import THEMES
        t_palette = THEMES.get(self.current_theme, THEMES["light"])

        ext = doc_path.suffix.lower()
        custom_app = self._get_external_app_for_ext(ext)

        msg_unsupported  = self.t("error_unsupported")
        lbl_open_default = self.translations.get(self.current_language, {}).get(
            "open_with_default_app", "Ouvrir dans l'application par défaut")
        lbl_open_custom  = f"Ouvrir avec {custom_app['name']}" if custom_app else ""

        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
            body {{ font-family: sans-serif; display: flex; flex-direction: column;
                   align-items: center; justify-content: center; height: 80vh; margin: 0;
                   background: {t_palette['bg']}; color: {t_palette['text']}; }}
            .icon {{ font-size: 56px; margin-bottom: 16px; opacity: .45; }}
            h2 {{ font-weight: 600; margin-bottom: 8px; color: {t_palette['text']}; }}
            p  {{ color: {t_palette['text_secondary']}; margin-bottom: 28px; font-size: 14px; }}
            .btn {{ display: inline-block; padding: 10px 24px; border-radius: 8px; cursor: pointer;
                   font-size: 14px; font-weight: 500; border: none; margin: 6px; }}
            .btn-primary {{ background: {t_palette['accent']}; color: #fff; }}
            .btn-secondary {{ background: {t_palette['surface2']};
                              color: {t_palette['text']}; border: 1px solid {t_palette['border']}; }}
        </style></head><body>
            <div class="icon">📄</div>
            <h2>{doc_path.name}</h2>
            <p>{msg_unsupported}</p>
            <button class="btn btn-primary" onclick="pyOpenDefault()">{lbl_open_default}</button>
            {"<button class='btn btn-secondary' onclick='pyOpenCustom()'>" + lbl_open_custom + "</button>" if custom_app else ""}
            <script>
                function pyOpenDefault() {{
                    history.pushState(null,'','?action=open_default');
                }}
                function pyOpenCustom() {{
                    history.pushState(null,'','?action=open_custom');
                }}
            </script>
        </body></html>"""

        self._unsupported_path   = doc_path
        self._unsupported_custom = custom_app

        if WEB_ENGINE_AVAILABLE and self.html_preview:
            # Déconnecter les signaux précédents avant de réutiliser
            try:
                self.html_preview.page().urlChanged.disconnect()
            except Exception:
                pass
            self._webview_set_html(html)
            self.html_preview.page().urlChanged.connect(self._on_unsupported_url_changed)
            self.preview_stack.setCurrentWidget(self.html_preview)
        else:
            self.show_text_preview(f"{doc_path.name}\n\n{msg_unsupported}")

    def _on_unsupported_url_changed(self, url):
        """Intercepte les pseudo-navigations JS pour déclencher l'ouverture externe."""
        qs = url.query()
        if "action=open_default" in qs:
            self.open_current_file_with_default_app()
            if hasattr(self, '_unsupported_path'):
                self._show_unsupported_file(self._unsupported_path)
        elif "action=open_custom" in qs:
            self._open_file_with_custom_app(
                getattr(self, '_unsupported_path', None),
                getattr(self, '_unsupported_custom', None)
            )
            if hasattr(self, '_unsupported_path'):
                self._show_unsupported_file(self._unsupported_path)

    def _get_external_app_for_ext(self, ext: str) -> dict | None:
        """
        Lit externe.cfg à la racine de USER_DATA_DIR.
        Retourne {"name": ..., "path": ..., "params": ...} ou None.

        Format de externe.cfg :
            Extension.MP3
            Chemin.MP3 = C:\\Program Files\\VLC\\vlc.exe
            Parametres.MP3 = --fullscreen

            Extension.URL
            Chemin.URL = C:\\...\\chrome.exe
            Parametres.URL = --incognito
        """
        cfg_path = config.USER_DATA_DIR / "externe.cfg"
        if not cfg_path.exists():
            return None
        try:
            ext_key = ext.lstrip(".").upper()
            app: dict = {}
            current_ext: str | None = None
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.lower().startswith("extension."):
                        current_ext = line.split(".", 1)[1].strip().upper()
                    elif current_ext == ext_key and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip().lower()
                        val = val.strip()
                        if key.startswith("chemin."):
                            app["path"] = val
                            app["name"] = Path(val).stem
                        elif key.startswith("parametres.") or key.startswith("parametre."):
                            app["params"] = val
            return app if "path" in app else None
        except Exception as e:
            print(f"[WARN] externe.cfg: {e}")
            return None

    def _open_file_with_custom_app(self, file_path, app_cfg):
        """Lance un fichier avec l'application configurée dans externe.cfg."""
        if not file_path or not app_cfg:
            return
        try:
            exe    = app_cfg.get("path", "")
            params = app_cfg.get("params", "").split() if app_cfg.get("params") else []
            cmd    = [exe] + params + [str(file_path)]
            from database.path_utils import _clean_env_for_subprocess
            subprocess.Popen(cmd, env=_clean_env_for_subprocess())
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"),
                                f"Impossible de lancer l'application :\n{e}")

    def _show_markdown_preview(self, doc_path):
        """Affiche un fichier Markdown rendu en HTML dans QWebEngineView."""
        try:
            with open(win_path(doc_path), "r", encoding="utf-8", errors="ignore") as f:
                md_text = f.read()

            try:
                import markdown as md_lib
                html_body = md_lib.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])
            except ImportError:
                # Fallback sans la bibliothèque markdown : conversion minimale
                import re, html as html_lib
                escaped = html_lib.escape(md_text)
                html_body = re.sub(r'^# (.+)$',   r'<h1>\1</h1>', escaped, flags=re.MULTILINE)
                html_body = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
                html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
                html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
                html_body = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         html_body)
                html_body = re.sub(r'`(.+?)`',        r'<code>\1</code>',     html_body)
                html_body = html_body.replace('\n', '<br>')

            from styles import THEMES
            t = THEMES.get(self.current_theme, THEMES["light"])
            full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
                body {{ font-family: -apple-system, 'Segoe UI', sans-serif; padding: 24px;
                        max-width: 960px; margin: auto; background: {t['bg']};
                        color: {t['text']}; line-height: 1.7; }}
                h1,h2,h3,h4 {{ color: {t['accent']}; margin-top: 1.4em; }}
                h1 {{ border-bottom: 2px solid {t['border']}; padding-bottom: .3em; }}
                code {{ background: {t['surface2']}; padding: 2px 6px; border-radius: 4px;
                        font-size: .9em; font-family: monospace; }}
                pre  {{ background: {t['surface2']}; padding: 14px; border-radius: 8px;
                        overflow-x: auto; }}
                pre code {{ background: transparent; padding: 0; }}
                blockquote {{ border-left: 4px solid {t['accent']}; margin: 0; padding-left: 16px;
                              color: {t['text_secondary']}; font-style: italic; }}
                table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
                th,td {{ border: 1px solid {t['border']}; padding: 8px 14px; text-align: left; }}
                th {{ background: {t['surface2']}; font-weight: 600; }}
                a {{ color: {t['accent']}; }}
                hr {{ border: none; border-top: 1px solid {t['border']}; }}
            </style></head><body>{html_body}</body></html>"""

            self.show_html_preview(full_html)

        except Exception as e:
            self.show_text_preview(f"Erreur lecture Markdown : {e}")

    def show_mhtml_preview(self, doc_path):
        """Prévisualise un fichier MHTML via QWebEngineView (support natif)."""
        if not WEB_ENGINE_AVAILABLE or not self.html_preview:
            self.show_text_preview(self.t("error_webengine_unavailable"))
            return
        self._webview_load_url(QUrl.fromLocalFile(str(doc_path)))
        self.preview_stack.setCurrentWidget(self.html_preview)

    def show_eml_preview(self, doc_path):
        """Prévisualise un fichier EML en extrayant le corps HTML ou texte."""
        import email as email_lib
        from email import policy

        try:
            with open(str(doc_path), "rb") as f:
                msg = email_lib.message_from_binary_file(f, policy=policy.default)

            # Métadonnées
            subject = msg.get("Subject", "")
            from_addr = msg.get("From", "")
            to_addr = msg.get("To", "")
            date = msg.get("Date", "")

            header_html = f"""
            <div style="background:#f5f5f5;padding:12px 16px;border-bottom:1px solid #ddd;
                        font-family:sans-serif;font-size:13px;color:#333;">
                <b>De :</b> {from_addr}<br>
                <b>À :</b> {to_addr}<br>
                <b>Sujet :</b> {subject}<br>
                <b>Date :</b> {date}
            </div>
            """

            # Corps : HTML en priorité, sinon texte plain
            body_html = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/html":
                        body_html = part.get_content()
                        break
                if not body_html:
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            text = part.get_content()
                            body_html = f"<pre style='font-family:sans-serif;padding:16px'>{text}</pre>"
                            break
            else:
                ct = msg.get_content_type()
                if ct == "text/html":
                    body_html = msg.get_content()
                else:
                    text = msg.get_content()
                    body_html = f"<pre style='font-family:sans-serif;padding:16px'>{text}</pre>"

            full_html = f"<html><body>{header_html}{body_html}</body></html>"
            self.show_html_preview(full_html)

        except Exception as e:
            self.show_text_preview(f"Erreur lecture EML : {e}")

    def _webview_set_html(self, html: str, base_url: QUrl = None):
        """
        Charge du HTML dans le QWebEngineView unique.
        Ajoute un timestamp invisible pour forcer QWebEngine à toujours
        re-rendre, même si le contenu est identique au précédent.
        Fonctionne sans timer (synchrone) — pas de race condition possible.
        """
        if not self.html_preview:
            return
        import time
        ts = int(time.time() * 1000)
        # Injecter un élément invisible unique → WebEngine voit toujours du "nouveau" contenu
        forced = html + f'<span id="_ged_r{ts}" style="display:none"></span>'
        if base_url:
            self.html_preview.setHtml(forced, base_url)
        else:
            self.html_preview.setHtml(forced)

    def _webview_load_url(self, url: QUrl):
        """
        Charge un fichier local dans le QWebEngineView unique.
        Lit le contenu et utilise setHtml() avec la base URL du fichier,
        ce qui garantit le rechargement même si l'URL est identique,
        tout en conservant la résolution des ressources relatives (images, CSS).
        Pour MHTML : utilise setUrl avec un fragment unique.
        """
        if not self.html_preview:
            return
        local = url.toLocalFile()
        if local:
            suffix = local.rsplit('.', 1)[-1].lower() if '.' in local else ''
            if suffix in ('mhtml', 'mht'):
                # MHTML : format binaire multipart, setHtml ne fonctionne pas
                # → forcer via fragment unique dans l'URL
                import time
                furl = QUrl(url)
                furl.setFragment(f"_r{int(time.time()*1000)}")
                self.html_preview.load(furl)
                return
            try:
                with open(local, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self._webview_set_html(content, url)
                return
            except Exception:
                pass
        # Fallback (URL non-locale)
        self.html_preview.load(url)

    def show_html_preview(self, html: str):
        """Affiche du HTML dans le QWebEngineView UNIQUE (jamais recréé)."""
        if not WEB_ENGINE_AVAILABLE or not self.html_preview:
            self.show_text_preview(html)
            return
        self._webview_set_html(html)
        self.preview_stack.setCurrentWidget(self.html_preview)

    def show_ods_preview(self, rel_path):
        import pandas as pd
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView

        file_path = config.FILES_DIR / rel_path
        self.xlsx_tab_widget.clear()

        try:
            xls = pd.ExcelFile(win_path(file_path), engine="odf")
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, engine="odf")

                table = QTableWidget()
                table.setEditTriggers(QAbstractItemView.NoEditTriggers)
                table.setRowCount(df.shape[0])
                table.setColumnCount(df.shape[1])
                # Définir les en-têtes de colonnes AVANT de remplir les cellules
                table.setHorizontalHeaderLabels([
                    "" if str(col).startswith("Unnamed") else str(col)
                    for col in df.columns
                ])

                # Remplir les cellules
                for i, row in df.iterrows():
                    for j, value in enumerate(row):
                        display_value = "" if pd.isna(value) else str(value)
                        table.setItem(i, j, QTableWidgetItem(display_value))

                table.resizeColumnsToContents()
                table.resizeRowsToContents()
                self.xlsx_tab_widget.addTab(table, sheet_name)

            self.xlsx_tab_widget.setVisible(True)
            self.preview_stack.setCurrentWidget(self.xlsx_tab_widget)

        except Exception as e:
            self.show_text_preview(self.t("textfile_read_error").format(error=str(e)))

    def show_xml_preview(self, rel_path):
        file_path = config.FILES_DIR / rel_path
        if not WEB_ENGINE_AVAILABLE or not self.html_preview:
            self.show_text_preview(self.t("disabled_html_preview"))
            return
        self._webview_load_url(QUrl.fromLocalFile(str(file_path)))
        self.preview_stack.setCurrentWidget(self.html_preview)

    def show_svg_preview(self, rel_path):
        file_path = config.FILES_DIR / rel_path

        if not WEB_ENGINE_AVAILABLE or not self.html_preview:
            self.show_text_preview(self.t("disabled_html_preview"))
            return

        try:
            svg_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.show_text_preview(f"Erreur lecture SVG : {e}")
            return

        from styles import THEMES
        t = THEMES.get(self.current_theme, THEMES["light"])
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
            html,body {{ margin:0; padding:0; background:{t['bg']};
                         display:flex; align-items:center; justify-content:center;
                         width:100%; height:100%; overflow:auto; }}
            svg {{ max-width:100%; max-height:100%; }}
        </style></head><body>{svg_content}</body></html>"""

        self._webview_set_html(html)
        self.preview_stack.setCurrentWidget(self.html_preview)
        self.zoom_controls_widget.show()
        self.prev_page_button.hide()
        self.next_page_button.hide()
        self.zoom_label.setText(f"{self.t('zoom')}100%")
        # SVG zoom via html_preview
        self.svg_web_view = self.html_preview

    def filter_documents(self, text):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            self._filter_tree_item(top_item, text)

    def _filter_tree_item(self, item, query):
        match = query in item.text(0).lower()
        has_visible_child = False

        for i in range(item.childCount()):
            child = item.child(i)
            child_visible = self._filter_tree_item(child, query)
            has_visible_child = has_visible_child or child_visible

        visible = match or has_visible_child
        item.setHidden(not visible)
        return visible


    def perform_search(self):
        raw = self.search_input.text().strip().lower()
        if not raw:
            return

        keywords = [kw for kw in raw.replace(",", " ").split() if kw]
        if not keywords:
            return

        # --- Prépare l'UI ---
        self._is_searching = True
        self._search_aborted = False
        self.search_result_count = 0
        self.search_count_label.setText(self.t("search_results_count_label").format(count=0))
        self.search_count_label.show()
        self.tree.clear()
        self.show_progress_bar_fade()
        self.progress_label.setText(self.t("search_in_progress"))
        self.progress_label.show()
        self.progress_bar.setMaximum(0)
        self.progress_bar.show()
        self.stop_search_button.setEnabled(True)
        self.stop_search_button.setVisible(True)
        self.reset_button.setEnabled(False)

        # --- Thread & Worker sans deleteLater() ---
        thread = QThread(self)
        worker = SearchWorker(keywords, self.t)
        worker.moveToThread(thread)

        # Connexions
        thread.started.connect(worker.run)
        worker.result_found.connect(self.display_search_result)
        worker.progress.connect(self._update_progress_value)
        worker.error.connect(self.on_search_error)
        worker.finished.connect(self.on_search_finished)
        worker.finished.connect(thread.quit)    # arrête le thread au finish

        # Sauvegarde pour pouvoir arrêter/réinitialiser plus tard
        self.search_thread = thread
        self.search_worker = worker
        thread.start()




    def display_search_result(self, doc):
        # 1) Si on a déjà reset, on ne fait plus rien
        if not self._is_searching:
            return

        rel_path = doc[2]
        parts = rel_path.split(os.sep)
        parent = None
        path_accumulator = []

        for i, part in enumerate(parts):
            path_accumulator.append(part)
            current_path = os.sep.join(path_accumulator)

            if i == len(parts) - 1:
                file_item = QTreeWidgetItem([part])
                file_item.setData(0, Qt.ItemDataRole.UserRole, rel_path)
                if parent:
                    parent.addChild(file_item)
                else:
                    self.tree.addTopLevelItem(file_item)

                p = file_item.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()

                file_item.setSelected(True)
                self.tree.scrollToItem(file_item)

            else:
                existing = self.find_tree_item(part, parent)
                if existing:
                    folder_item = existing
                else:
                    folder_item = QTreeWidgetItem([part])
                    if parent:
                        parent.addChild(folder_item)
                    else:
                        self.tree.addTopLevelItem(folder_item)
                parent = folder_item
        
        # 3) Mettre à jour le compteur
        self.search_result_count += 1
        self.search_count_label.setText(
            self.t("search_results_count_label").format(count=self.search_result_count)
        )


    def on_search_finished(self):
        # la recherche est finie (normalement ou par stop_search)
        self.hide_progress_bar_fade()
        self.stop_search_button.setVisible(False)

        # On autorise enfin la réinitialisation
        self.reset_button.setEnabled(True)

        if self._search_aborted:
            # on cache simplement le compteur
            self.search_count_label.hide()
        else:
            # fin normale : on affiche message si zéro résultat
            if self.search_result_count == 0:
                QMessageBox.information(
                    self,
                    self.t("search_no_result_title"),
                    self.t("search_no_result_message")
                )
                self.search_count_label.hide()
            else:
                # on remet à jour le label s'il y a eu des résultats
                self.search_count_label.setText(
                    self.t("search_results_count_label").format(count=self.search_result_count)
                )

        # Et on coupe proprement le thread s'il n'est pas encore terminé
        thr = getattr(self, 'search_thread', None)
        if thr and thr.isRunning():
            thr.quit()
            thr.wait()
        self.search_thread = None
        self.search_worker = None

                

    def reset_ui(self):
        # ne touche pas au thread ni au worker : ils sont déjà terminés
        self._is_searching = False
        self._search_aborted = False

        # UI
        self.search_input.clear()
        self.tree.clear()
        self.search_count_label.clear()
        self.search_count_label.hide()
        self.hide_progress_bar_fade()  # masque bar & label de prog
        self.progress_label.clear()
        self.progress_label.hide()
        self.progress_bar.reset()
        self.progress_bar.hide()
        self.stop_search_button.setVisible(False)

        # remet l'arborescence par défaut
        self.load_documents()
        self.clear_preview()
        self.update_file_count()

        # désactive le bouton 'Réinitialiser' jusqu'à la prochaine recherche
        self.reset_button.setEnabled(False)

    def refresh_ui(self):
        """
        Vide la prévisualisation et remet
        l'arborescence + l'UI au Â« state Â» de démarrage.
        """
        # 1) Vider la preview
        self.clear_preview()
        
        # 2) Recharger l'arborescence complète
        self.tree.clear()
        self.load_documents()
        
        # 3) Cacher/vider tous les éléments de recherche
        self.search_input.clear()
        self.search_count_label.clear()
        self.search_count_label.hide()
        self.progress_bar.reset()
        self.progress_bar.hide()
        self.progress_label.clear()
        self.progress_label.hide()
        self.stop_search_button.setVisible(False)
        
        # 4) Remettre l'état des métadonnées à Â« vide Â»
        self.set_metadata_fields_enabled(False)
        self.toggle_metadata_button.setChecked(False)
        self.metadata_form.hide()
        
        # 5) Réinitialiser les var. internes si besoin
        self.pdf_doc = None
        self.original_pixmap = None
        self.current_zoom = 1.0
        self.current_pdf_page = 0




    def on_search_error(self, error):
        self.hide_progress_bar_fade()
        QMessageBox.critical(self, self.t("search_error_title"), str(error))

    def stop_search(self):
        # désactive toute suite de résultats
        self._search_aborted = True
        self._is_searching   = False
        self.stop_search_button.setEnabled(False)
        if getattr(self, 'search_worker', None):
            self.search_worker.stop()




    def find_tree_item(self, name, parent=None):
        if parent is None:
            # Cherche parmi les top-level
            count = self.tree.topLevelItemCount()
            for i in range(count):
                item = self.tree.topLevelItem(i)
                if item.text(0) == name:
                    return item
        else:
            # Cherche parmi les enfants
            count = parent.childCount()
            for i in range(count):
                item = parent.child(i)
                if item.text(0) == name:
                    return item
        return None

    def toggle_theme(self):
        dlg = ThemePickerDialog(self.current_theme, self.t, parent=self)
        # Centrer sur la fenêtre principale
        dlg.adjustSize()
        center = self.geometry().center()
        dlg.move(center.x() - dlg.width() // 2, center.y() - dlg.height() // 2)
        if dlg.exec() == QDialog.Accepted:
            self.apply_theme(dlg.selected_theme)

    # Thèmes considérés comme "sombres" pour le logo et les icônes
    DARK_THEMES = {"dark", "twilight", "ocean", "forest", "sunset",
                   "rose", "slate", "midnight", "brown"}

    # ── Bouton accordéon sidebar ──────────────────────────────────────────────

    def _update_sidebar_btn_style(self):
        from styles import THEMES
        p  = THEMES.get(self.current_theme, THEMES["light"])
        r  = 13
        self._sidebar_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p["surface"]};
                border: 1.5px solid {p["border"]};
                border-radius: {r}px;
            }}
            QPushButton:hover {{
                background: {p["surface2"]};
                border: 1.5px solid {p["accent"]};
            }}
            QPushButton:pressed {{
                background: {p["hover"]};
                border: 1.5px solid {p["accent"]};
            }}
        """)
        # Opacité via QGraphicsOpacityEffect
        if not hasattr(self, "_sidebar_btn_effect"):
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            self._sidebar_btn_effect = QGraphicsOpacityEffect(self._sidebar_btn)
            self._sidebar_btn.setGraphicsEffect(self._sidebar_btn_effect)
            self._sidebar_btn.installEventFilter(self)
        self._sidebar_btn_effect.setOpacity(0.32)

    def _update_sidebar_btn_icon(self):
        import qtawesome as qta
        name = "fa5s.chevron-left" if self._sidebar_open else "fa5s.chevron-right"
        self._sidebar_btn.setIcon(qta.icon(name, color=self._accent_color(), scale_factor=0.5))

    def _accent_color(self) -> str:
        from styles import THEMES
        return THEMES.get(self.current_theme, THEMES["light"])["accent"]

    def _reposition_sidebar_btn(self):
        """Centre le bouton exactement sur la poignée du splitter, à mi-hauteur."""
        if not hasattr(self, "_sidebar_btn") or self.splitter.count() < 2:
            return
        handle = self.splitter.handle(1)
        if handle is None:
            return

        bw = self._sidebar_btn.width()
        bh = self._sidebar_btn.height()

        # Utiliser mapToParent pour tenir compte des marges du layout
        handle_pos = handle.mapToParent(handle.rect().topLeft())
        hx = handle_pos.x()
        hw = handle.width()

        # Centrer sur la poignée, toujours visible (min 6 px du bord gauche)
        btn_x = max(6, hx + hw // 2 - bw // 2)

        # Centré verticalement dans la zone du splitter
        splitter_pos = self.splitter.mapToParent(self.splitter.rect().topLeft())
        btn_y = splitter_pos.y() + self.splitter.height() // 2 - bh // 2

        self._sidebar_btn.move(btn_x, btn_y)
        self._sidebar_btn.raise_()

    def _toggle_sidebar(self):
        # Garde anti-double-clic basé sur un flag (pas sur l'état de l'animation)
        if getattr(self, "_sidebar_animating", False):
            return
        self._sidebar_animating = True

        sizes = self.splitter.sizes()
        total = sum(sizes)

        if self._sidebar_open:
            self._sidebar_saved = max(sizes[0], 180)
            from_v, to_v = sizes[0], 0
        else:
            from_v, to_v = 0, self._sidebar_saved

        # QVariantAnimation : pas besoin de proxy ni de Q_PROPERTY
        from PySide6.QtCore import QVariantAnimation
        anim = QVariantAnimation(self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(float(from_v))
        anim.setEndValue(float(to_v))

        def _on_v(v):
            iv = int(v)
            self.splitter.setSizes([iv, max(total - iv, 0)])
            self._reposition_sidebar_btn()

        def _on_done():
            self._sidebar_animating = False
            self._sidebar_open = (to_v > 0)
            self._update_sidebar_btn_icon()
            self._reposition_sidebar_btn()

        anim.valueChanged.connect(_on_v)
        anim.finished.connect(_on_done)
        anim.start()
        self._sidebar_anim = anim   # maintenir en vie

    def _pick_item_dialog(self, title: str, label: str, items: list) -> tuple:
        """
        Remplace QInputDialog.getItem() avec des boutons traduits via notre système i18n.
        Retourne (selected_text, ok: bool).
        """
        from styles import THEMES, get_message_box_style
        p = THEMES.get(self.current_theme, THEMES["light"])

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(320)
        dlg.setStyleSheet(get_message_box_style(self.current_theme))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel(label)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        combo = QComboBox()
        combo.addItems(items)
        combo.setStyleSheet(f"background: {p['surface2']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 6px; padding: 4px;")
        layout.addWidget(combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(self.t("btn_cancel"))
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(dlg.reject)

        btn_ok = QPushButton(self.t("btn_ok"))
        btn_ok.setFixedWidth(90)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(dlg.accept)
        btn_ok.setStyleSheet(f"background: {p['accent']}; color: #fff; border: none; border-radius: 6px; padding: 6px;")

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        result = dlg.exec()
        return (combo.currentText(), result == QDialog.Accepted)

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        # Sauvegarder en premier — avant toute opération qui pourrait échouer
        config.save_user_theme(theme_name)
        from styles import get_full_stylesheet, get_scrollbar_style
        stylesheet = get_full_stylesheet(theme_name) + get_zoom_button_style(theme_name) + get_scrollbar_style(theme_name)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        QApplication.setPalette(self.get_palette_for_theme(theme_name))
        self.setStyleSheet(stylesheet)
        QApplication.instance().setStyleSheet(stylesheet)
        self.text_preview.setStyleSheet(get_text_preview_style(theme_name))
        apply_common_styles(self)
        if hasattr(self, "folder_browser"):
            self.folder_browser.set_theme(theme_name)
        if hasattr(self, "tree") and self.tree.itemDelegate():
            from styles import THEMES as _TH
            _tp = _TH.get(theme_name, _TH["light"])
            self.tree.itemDelegate().accent_color = _tp["accent"]
            self.tree.viewport().update()
        if hasattr(self, "_sidebar_btn"):
            self._update_sidebar_btn_style()
            self._update_sidebar_btn_icon()
        self.update_logo()

    def get_palette_for_theme(self, theme_name: str) -> QPalette:
        from styles import THEMES
        t = THEMES.get(theme_name, THEMES["light"])
        palette = QPalette()
        palette.setColor(QPalette.Window,          QColor(t["bg"]))
        palette.setColor(QPalette.WindowText,      QColor(t["text"]))
        palette.setColor(QPalette.Base,            QColor(t["surface"]))
        palette.setColor(QPalette.Text,            QColor(t["text"]))
        palette.setColor(QPalette.ToolTipBase,     QColor(t["surface"]))
        palette.setColor(QPalette.ToolTipText,     QColor(t["text"]))
        palette.setColor(QPalette.Button,          QColor(t["surface2"]))
        palette.setColor(QPalette.ButtonText,      QColor(t["text"]))
        palette.setColor(QPalette.Highlight,       QColor(t["accent"]))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        return palette


    def apply_light_theme(self):
        self.apply_theme("light")

    def apply_dark_theme(self):
        self.apply_theme("dark")
    
    def get_light_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#fdfdfd"))
        palette.setColor(QPalette.WindowText, QColor("#202020"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#202020"))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#000000"))
        palette.setColor(QPalette.Button, QColor("#f4f4f4"))
        palette.setColor(QPalette.ButtonText, QColor("#202020"))
        return palette

    def get_dark_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#2e2e2e"))
        palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.Base, QColor("#3c3c3c"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipBase, QColor("#333333"))
        palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.Button, QColor("#444444"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        return palette

    def apply_button_styles(self):
        style = get_theme_button_style(self.current_theme)

        for btn in [
            self.reindex_button,
            self.import_button,
            self.reset_button,
            self.theme_button,
            self.search_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.prev_page_button,
            self.next_page_button
        ]:
            btn.setStyleSheet(style)
            btn.setFixedSize(40, 40)


    def load_metadata(self, rel_path):
        full_path = config.FILES_DIR / rel_path  

        if full_path.is_dir():  # Correction ici
            self.set_metadata_fields_enabled(False)
            self.toggle_metadata_button.setEnabled(False)
            self.metadata_form.hide()
            return

        try:
            with sqlite3.connect(config.DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT author, tags, comment, version, updated_at
                    FROM document_metadata
                    WHERE document_path = ?
                """, (rel_path,))
                row = cur.fetchone()

            if row:
                author, tags_text, comment, version, updated_at = row

                self.meta_author_field.setText(author or "")
                self.meta_comment_field.setPlainText(comment or "")
                self.meta_version_field.setText(version or "")
                self.meta_updated_field.setText(updated_at or "")

                # === CHARGEMENT DES TAGS ===
                self.current_tags = []
                self.clear_tags_from_layout()


                for tag in [t.strip() for t in (tags_text or "").split(",") if t.strip()]:
                    self.add_tag(tag)

            else:
                # Aucun metadata connu â†’ réinitialiser
                self.meta_author_field.clear()
                self.meta_comment_field.clear()
                self.meta_version_field.clear()
                self.meta_updated_field.clear()

                self.current_tags = []
                self.clear_tags_from_layout()


            self.current_metadata_path = rel_path
            self.set_metadata_fields_enabled(True)
            self.toggle_metadata_button.setEnabled(True)

        except Exception as e:
            print(f"[ERREUR] Chargement métadonnées depuis la base pour {rel_path} : {e}")
            self.set_metadata_fields_enabled(False)
            self.toggle_metadata_button.setEnabled(False)
            self.metadata_form.hide()



    def save_current_metadata(self):
        if not hasattr(self, "current_metadata_path") or not self.current_metadata_path:
            print("[ERREUR] Aucune métadonnée en cours à sauvegarder.")
            return  # On arrête la fonction si le chemin des métadonnées est invalide ou non défini

        metadata = {
            "author": self.meta_author_field.text(),
            "tags": ", ".join(self.current_tags),
            "comment": self.meta_comment_field.toPlainText(),
            "version": self.meta_version_field.text(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Sauvegarde en base
        save_metadata_to_db(self.current_metadata_path, metadata)

        print(f"[DEBUG] Sauvegarde en base des métadonnées : {self.current_metadata_path}")

        self.meta_updated_field.setText(metadata["updated_at"])
        self.save_confirmation_label.setText(self.t("metadata_saved"))
        self.save_confirmation_label.show()
        QTimer.singleShot(2000, self.save_confirmation_label.hide)

        # Rafraîchir la liste des tags dans le combo (intègre le nouveau tag)
        self.refresh_tag_suggestions()



    def set_metadata_fields_enabled(self, enabled: bool):
        self.meta_author_field.setEnabled(enabled)
        self.meta_comment_field.setEnabled(enabled)
        self.meta_version_field.setEnabled(enabled)
        self.meta_updated_field.setEnabled(enabled)  # <--- indispensable
        self.save_metadata_button.setEnabled(enabled)

    def toggle_metadata_visibility(self):
        is_open = self.toggle_metadata_button.isChecked()
        icon_name = "fa5s.angle-up" if is_open else "fa5s.angle-down"
        self.toggle_metadata_button.setIcon(qta.icon(icon_name, color="#007BFF"))

        self.metadata_animation.stop()

        if is_open:
            self.metadata_form.setMaximumHeight(0)
            self.metadata_form.show()

            # Calcul de la hauteur cible sans sizeHint (biaisé par les chips)
            # Sommer les hauteurs minimales connues de chaque rangée
            tags_h    = max(self.meta_tags_container.minimumHeight(), 64)
            comment_h = self.meta_comment_field.minimumHeight()
            field_h   = 30   # ligne auteur / version / modifié le
            button_h  = 40   # bouton Enregistrer
            spacing   = self.metadata_layout.verticalSpacing()
            margins   = (self.metadata_layout.contentsMargins().top()
                         + self.metadata_layout.contentsMargins().bottom())
            target_h  = (
                field_h   +   # auteur       (row 0)
                tags_h    +   # tags          (row 1)
                comment_h +   # commentaire   (row 2)
                field_h   +   # version       (row 3)
                field_h   +   # modifié le    (row 4)
                button_h  +   # enregistrer   (row 5)
                spacing * 5 + margins + 8
            )

            self.metadata_animation.setStartValue(0)
            self.metadata_animation.setEndValue(target_h)
        else:
            self.metadata_animation.setStartValue(self.metadata_form.height())
            self.metadata_animation.setEndValue(0)

        self.metadata_animation.start()

    def on_metadata_animation_finished(self):
        if self.toggle_metadata_button.isChecked():
            # Libérer la contrainte de hauteur max → le formulaire peut
            # s'adapter librement si les tags occupent plusieurs lignes
            self.metadata_form.setMaximumHeight(16777215)
        else:
            self.metadata_form.hide()

    def add_tag_from_input(self):
        """Conservé pour compatibilité — non utilisé avec le nouveau TagPickerDialog."""
        pass

    def clear_tags_from_layout(self):
        """Supprime tous les widgets de tags du FlowLayout."""
        for i in reversed(range(self.meta_tags_layout.count())):
            item = self.meta_tags_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
                widget.setParent(None)

    def on_tag_typing(self, text):
        """Conservé pour compatibilité — non utilisé avec le nouveau TagPickerDialog."""
        pass

    def add_tag(self, tag):
        """Ajoute un tag par programmation (utilisé par load_metadata)."""
        if not tag or any(t.casefold() == tag.casefold() for t in self.current_tags):
            return
        widget = self.create_tag_widget(tag)
        self.meta_tags_layout.addWidget(widget)
        self.current_tags.append(tag)

    def remove_tag(self, widget):
        tag = widget.property("tag_text")
        if tag in self.current_tags:
            self.current_tags.remove(tag)
        widget.setParent(None)
        widget.deleteLater()

    def setup_metadata_tags_field(self):
        self.current_tags = []

        # Zone d'affichage des tags sélectionnés (pilules colorées)
        self.meta_tags_display = QWidget()
        self.meta_tags_layout  = FlowLayout()
        self.meta_tags_display.setLayout(self.meta_tags_layout)

        # Bouton d'ouverture du gestionnaire de tags
        self.meta_tag_open_btn = QPushButton()
        self.meta_tag_open_btn.setIcon(qta.icon("fa5s.tags", color="#007BFF"))
        self.meta_tag_open_btn.setText("  Gérer les tags…")
        self.meta_tag_open_btn.setFixedHeight(28)
        self.meta_tag_open_btn.setCursor(Qt.PointingHandCursor)
        self.meta_tag_open_btn.clicked.connect(self._open_tag_picker)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addWidget(self.meta_tag_open_btn)
        btn_row.addStretch()

        self.meta_tags_container = QWidget()
        cl = QVBoxLayout(self.meta_tags_container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)
        cl.addWidget(self.meta_tags_display)
        cl.addLayout(btn_row)
        self.meta_tags_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.meta_tags_container.setMinimumHeight(60)

        self.label_tags = QLabel(self.t("label_tags"))
        self.metadata_layout.addWidget(self.label_tags, 1, 0, Qt.AlignTop)
        self.metadata_layout.addWidget(self.meta_tags_container, 1, 1)
        # Hauteur minimale garantie pour la rangée tags (pilules + bouton)
        self.metadata_layout.setRowMinimumHeight(1, 64)

    def _open_tag_picker(self):
        """Ouvre le TagPickerDialog et applique le résultat."""
        # Fusionner tags DB + tags en mémoire (non encore enregistrés)
        db_tags = get_all_tags()
        all_tags = sorted(set(db_tags) | set(self.current_tags), key=str.casefold)
        dlg = TagPickerDialog(
            current_tags=list(self.current_tags),
            all_tags=all_tags,
            translate_fn=self.t,
            theme=self.current_theme,
            parent=self
        )
        if dlg.exec() != QDialog.Accepted:
            return

        # ── Opérations globales sur la DB ──────────────────────────────────
        if dlg.pending_rename:
            old_name, new_name = dlg.pending_rename
            self._rename_tag_in_db(old_name, new_name)

        for tag_to_del in dlg.pending_deletes:
            self._delete_tag_from_db(tag_to_del)

        # ── Mise à jour de l'affichage local ──────────────────────────────
        self.current_tags = dlg.current_tags
        self.clear_tags_from_layout()
        for tag in self.current_tags:
            widget = self.create_tag_widget(tag)
            self.meta_tags_layout.addWidget(widget)

        # Rafraîchir les suggestions
        self.refresh_tag_suggestions()

    def _rename_tag_in_db(self, old_name: str, new_name: str):
        """Renomme un tag dans document_metadata pour tous les documents."""
        try:
            with sqlite3.connect(config.DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT document_path, tags FROM document_metadata")
                rows = cur.fetchall()
                for path, tags_str in rows:
                    if not tags_str:
                        continue
                    tags = [t.strip() for t in tags_str.split(",")]
                    new_tags = [new_name if t.casefold() == old_name.casefold() else t
                                for t in tags]
                    if new_tags != tags:
                        cur.execute(
                            "UPDATE document_metadata SET tags=? WHERE document_path=?",
                            (", ".join(new_tags), path)
                        )
                conn.commit()
            self.statusBar().showMessage(
                f"✅  Tag « {old_name} » renommé en « {new_name} »", 4000)
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"),
                                f"Erreur renommage tag :\n{e}")

    def _delete_tag_from_db(self, tag_name: str):
        """Supprime un tag de document_metadata pour tous les documents."""
        try:
            with sqlite3.connect(config.DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT document_path, tags FROM document_metadata")
                rows = cur.fetchall()
                for path, tags_str in rows:
                    if not tags_str:
                        continue
                    tags = [t.strip() for t in tags_str.split(",")
                            if t.strip().casefold() != tag_name.casefold()]
                    cur.execute(
                        "UPDATE document_metadata SET tags=? WHERE document_path=?",
                        (", ".join(tags), path)
                    )
                conn.commit()
            self.statusBar().showMessage(
                f"✅  Tag « {tag_name} » supprimé de tous les documents", 4000)
        except Exception as e:
            QMessageBox.warning(self, self.t("error_title"),
                                f"Erreur suppression tag :\n{e}")

    
    def update_tag_input_icon(self):
        pass  # supprimé avec le QComboBox — conservé pour compatibilité

    def reposition_tag_input_arrow(self):
        pass  # supprimé avec le QComboBox — conservé pour compatibilité


    def create_tag_widget(self, tag):
        tag_widget = QWidget()
        tag_widget.setProperty("tag_text", tag)

        color = tag_color(tag)

        # Couleur assombrie pour le hover (déterministe, toujours lisible)
        r = int(int(color[1:3], 16) * 0.78)
        g = int(int(color[3:5], 16) * 0.78)
        b = int(int(color[5:7], 16) * 0.78)
        color_hover = f"#{r:02x}{g:02x}{b:02x}"

        tag_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {color};
                border-radius: 12px;
                padding: 4px 6px;
            }}
            QWidget:hover {{
                background-color: {color_hover};
            }}
        """)

        layout = QHBoxLayout(tag_widget)
        layout.setContentsMargins(8, 2, 6, 2)
        layout.setSpacing(4)

        label = QLabel(tag)
        label.setStyleSheet(
            "color: white; font-size: 11px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        label.setToolTip(tag)
        label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        remove_btn = QPushButton("×")
        remove_btn.setObjectName("tagRemoveButton")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton#tagRemoveButton {
                background-color: transparent;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
            }
            QPushButton#tagRemoveButton:hover {
                color: #ffcccc;
            }
        """)
        remove_btn.clicked.connect(lambda _, w=tag_widget: self.remove_tag(w))

        layout.addWidget(label)
        layout.addWidget(remove_btn)

        initial_width = 100
        expanded_width = 160

        tag_widget.setMinimumWidth(initial_width)
        tag_widget.setMaximumWidth(initial_width)
        tag_widget.setFixedHeight(tag_widget.sizeHint().height())
        tag_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        def enterEvent(event):
            tag_widget.raise_()
            container_width = tag_widget.parent().width()
            max_safe_width = container_width - tag_widget.pos().x() - 20
            target_width = min(expanded_width, max_safe_width)

            anim = QPropertyAnimation(tag_widget, b"minimumWidth")
            anim.setDuration(150)
            anim.setStartValue(tag_widget.width())
            anim.setEndValue(target_width)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            tag_widget.setMaximumWidth(target_width)
            tag_widget._anim = anim

        def leaveEvent(event):
            tag_widget.setMaximumWidth(initial_width)
            anim = QPropertyAnimation(tag_widget, b"minimumWidth")
            anim.setDuration(150)
            anim.setStartValue(tag_widget.width())
            anim.setEndValue(initial_width)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            tag_widget._anim = anim

        tag_widget.enterEvent = enterEvent
        tag_widget.leaveEvent = leaveEvent

        return tag_widget

    def load_metadata_fields(self, metadata):
        # === Ã‰tape 1 : purge propre ===
        self.clear_tags_from_layout()
        self.current_tags = []

        # === Ã‰tape 2 : chargement des champs simples ===
        self.meta_author_field.setText(metadata.get("author", ""))
        self.meta_comment_field.setPlainText(metadata.get("comment", ""))
        self.meta_version_field.setText(metadata.get("version", ""))
        self.meta_updated_field.setText(metadata.get("updated_at", ""))

        # === Ã‰tape 3 : chargement des tags (avec vérif) ===
        raw_tags = metadata.get("tags", "")
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [t.strip() for t in raw_tags if t.strip()]
        else:
            tags = []

        print(f"[DEBUG] Tags à charger : {tags}")

        for tag in tags:
            tag_widget = self.create_tag_widget(tag)
            self.meta_tags_layout.addWidget(tag_widget)
            self.current_tags.append(tag)


    def refresh_tag_suggestions(self):
        """Pas d'action nécessaire : les suggestions sont chargées à l'ouverture du TagPickerDialog."""
        pass


    def load_tag_filter(self):
        # 1) Vide et ajoute un placeholder 'Sélectionner un tag'
        self.tag_filter_combo.clear()
        placeholder = self.t("select_tag_filter")
        self.tag_filter_combo.addItem(placeholder)
        self.tag_filter_combo.model().item(0).setEnabled(False)

        # 2) Ajoute tous les tags existants
        tags = get_all_tags()  # renvoie la liste de tous les tags en base
        for tag in sorted(set(tags), key=str.lower):
            self.tag_filter_combo.addItem(tag)


 
    def _toggle_symlink_lock(self, rel_path: str, currently_locked: bool):
        """Bascule le verrou d'un symlink et persiste dans config.json."""
        if currently_locked:
            self.locked_symlinks.discard(rel_path)
        else:
            self.locked_symlinks.add(rel_path)
        config.save_locked_symlinks(self.locked_symlinks)
        # Rafraîchir l'arbre pour mettre à jour l'icône si besoin
        self.load_documents()

    def show_tree_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        rel_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not rel_path:
            return

        full_path = config.FILES_DIR / rel_path
        if not full_path.exists():
            return

        menu = QMenu(self)

        # 1) SYMLINK (fichier ou dossier)
        if _is_symlink_robust(full_path):
            real = full_path.resolve()
            is_locked = rel_path in self.locked_symlinks

            # Ouvrir la cible
            act_open = QAction(self.t("context_open_folder"), self)
            act_open.triggered.connect(lambda _, p=(real if real.is_dir() else real.parent):
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))))
            menu.addAction(act_open)

            # Ajouter des fichiers dans la cible si c'est un dossier
            if real.is_dir():
                act_add = QAction(self.t("context_add_files"), self)
                act_add.triggered.connect(lambda _, p=real: self._add_files_to_target_folder(p))
                menu.addAction(act_add)

            # Supprimer la cible
            act_del = QAction(self.t("context_delete_target"), self)
            act_del.triggered.connect(lambda _, link=full_path: self._delete_symlink_target(link))
            menu.addAction(act_del)

            menu.addSeparator()

            # Verrouillage du lien
            lock_label = (
                f"🔓  {self.t('symlink_unlock')}"
                if is_locked else
                f"🔒  {self.t('symlink_lock')}"
            )
            act_lock = QAction(lock_label, self)
            act_lock.triggered.connect(
                lambda _, rp=rel_path, locked=is_locked: self._toggle_symlink_lock(rp, locked)
            )
            menu.addAction(act_lock)

            # Indicateur visuel si verrouillé
            if is_locked:
                act_info = QAction(f"⚠️  {self.t('symlink_locked_info')}", self)
                act_info.setEnabled(False)
                menu.addAction(act_info)

        # 2) DOSSIER Â« NATIF Â»
        elif full_path.is_dir():
            act_open = QAction(self.t("context_open_folder"), self)
            act_open.triggered.connect(lambda: self.open_folder_for_item(rel_path))
            menu.addAction(act_open)

            act_add = QAction(self.t("context_add_files"), self)
            act_add.triggered.connect(lambda: self.add_files_to_folder(rel_path))
            menu.addAction(act_add)

            act_rename_ctx = QAction(self.t("rename_title"), self)
            act_rename_ctx.triggered.connect(lambda: self.rename_selected_item())
            menu.addAction(act_rename_ctx)

        # 3) FICHIER Â« NATIF Â»
        elif full_path.is_file():
            act_open = QAction(self.t("context_open_folder"), self)
            act_open.triggered.connect(lambda: self.open_folder_for_item(rel_path))
            menu.addAction(act_open)

            act_rename_ctx = QAction(self.t("rename_title"), self)
            act_rename_ctx.triggered.connect(lambda: self.rename_selected_item())
            menu.addAction(act_rename_ctx)

        # --- Option commune à tous (symlink ou non) : déplacer ---
        act_move = QAction(self.t("context_move_item"), self)
        act_move.triggered.connect(lambda: self.move_item_to_another_folder(rel_path))
        menu.addAction(act_move)

        menu.exec(self.tree.viewport().mapToGlobal(position))


    def open_folder_for_item(self, rel_path):
        folder_path = (config.FILES_DIR / rel_path).parent

        try:
            open_folder_in_explorer(folder_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                self.t("error_title"),
                self.t("error_open_folder").format(error=str(e))
            )

    def add_files_to_folder(self, rel_path):

        folder_path = config.FILES_DIR / rel_path
        if not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(self, self.t("error_title"), self.t("folder_not_found"))
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.t("select_files_to_add"),
            "",
            self.t("all_files_filter"),
            options=_file_dialog_options()
        )
        if not file_paths:
            return

        folder_name = Path(rel_path).name
        options = {
            "copy": self.t("import_mode_copy"),    # ex: "Copier"
            "link": self.t("import_mode_link")     # ex: "Créer un lien symbolique"
        }

        reverse_options = {v: k for k, v in options.items()}

        selected_text, ok = self._pick_item_dialog(
            self.t("import_mode_title"),
            self.t("import_mode_question"),
            list(options.values())
        )

        if not ok:
            return

        mode = reverse_options[selected_text]

        try:
            added_names = []
            for src in file_paths:
                src_path = Path(src)
                dest_path = folder_path / src_path.name

                if dest_path.exists():
                    reply = QMessageBox.question(
                        self,
                        self.t("file_exists_title"),
                        self.t("file_exists_message").format(name=src_path.name),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        continue

                # Copier ou créer le lien
                if mode == "copy":
                    shutil.copy2(str(src_path), str(dest_path))
                else:
                    try:
                        os.symlink(str(src_path), str(dest_path),
                                   target_is_directory=src_path.is_dir())
                    except (OSError, NotImplementedError):
                        if src_path.is_dir():
                            shutil.copytree(str(src_path), str(dest_path))
                        else:
                            shutil.copy2(str(src_path), str(dest_path))

                added_names.append(src_path.name)

            self.reindex_files()

            if added_names:
                QMessageBox.information(
                    self,
                    self.t("import_success_title"),
                    self.t("import_success_file_to_folder").format(
                        names=", ".join(added_names),
                        folder=Path(rel_path).name
                    )
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                self.t("import_error_title"),
                self.t("import_error_message").format(error=str(e))
            )

    def move_item_to_another_folder(self, rel_path):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import shutil

        source_path = config.FILES_DIR / rel_path
        if not source_path.exists():
            QMessageBox.warning(self, self.t("error_title"), self.t("file_not_found"))
            return

        # Garde verrou symlink
        if rel_path in self.locked_symlinks:
            answer = QMessageBox.question(
                self,
                self.t("symlink_locked_title"),
                self.t("symlink_locked_confirm_move").format(name=Path(rel_path).name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                return

        target_dir = QFileDialog.getExistingDirectory(
            self,
            self.t("select_target_folder"),
            str(config.FILES_DIR)
        )

        if not target_dir:
            return  # utilisateur a annulé

        target_dir = Path(target_dir)

        # Assure qu'on déplace bien dans le dossier `files/`
        if not str(target_dir).startswith(str(config.FILES_DIR)):
            QMessageBox.warning(self, self.t("error_title"), self.t("error_not_inside_ged"))
            return

        dest_path = target_dir / source_path.name

        if dest_path.exists():
            reply = QMessageBox.question(
                self,
                self.t("file_exists_title"),
                self.t("file_exists_message").format(name=dest_path.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            shutil.move(str(source_path), str(dest_path))
            self.reindex_files()
            msg = QMessageBox(self)
            msg.setWindowTitle(self.t("move_success_title"))
            msg.setText(self.t("move_success_message").format(name=source_path.name))
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.open()  # â† non bloquant

        except Exception as e:
            QMessageBox.critical(
                self,
                self.t("move_error_title"),
                self.t("move_error_message").format(error=str(e))
            )

    def _delete_symlink_target(self, link_path: Path):
        """
        Supprime le fichier/dossier pointé par link_path (symlink),
        puis relance la réindexation pour nettoyer la base et l'affichage.
        """
        real = link_path.resolve()
        # confirmation
        reply = QMessageBox.question(
            self,
            self.t("delete_confirm_title"),
            self.t("delete_confirm_text").format(path=str(real)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # suppression du réel
            if real.is_dir():
                shutil.rmtree(real)
            else:
                real.unlink()
            # on relance la réindexation pour supprimer aussi le symlink orphelin
            self.reindex_files()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.t("delete_error_title"),
                self.t("delete_error_text").format(path=str(real), error=str(e))
            )

    def _add_files_to_target_folder(self, real_folder: Path):
        """
        Ouvre un dialogue pour ajouter des fichiers DANS real_folder (hors /files),
        en créant des symlinks vers l'original ou en copiant en fallback.
        Puis réindexe pour mettre à jour l'arborescence.
        """
        from pathlib import Path
        import shutil, os
        # Sélection multi-fichiers
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.t("select_files_to_add"),
            "",
            self.t("all_files_filter"),
            options=_file_dialog_options()
        )
        if not file_paths:
            return

        added = []
        for src in file_paths:
            src = Path(src)
            dest = real_folder / src.name
            if dest.exists():
                # on peut proposer un overwrite ou skip suivant votre besoin
                continue
            try:
                os.symlink(str(src), str(dest))
            except (OSError, NotImplementedError):
                shutil.copy2(str(src), str(dest))
            added.append(src.name)

        if added:
            QMessageBox.information(
                self,
                self.t("import_success_title"),
                self.t("import_success_file_to_folder").format(
                    names=", ".join(added),
                    folder=str(real_folder)
                )
            )
        # on réindexe toute la base, y compris ce nouveau contenu
        self.reindex_files()

    def toggle_tag_filter(self):
        if self.tag_filter_combo.isVisible():
            self.tag_filter_combo.setVisible(False)
        else:
            self.refresh_tag_filter_list()
            self.tag_filter_combo.setVisible(True)

    def refresh_tag_filter_list(self):
        from database.db import get_all_tags
        tags = get_all_tags()
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem(self.t("select_tag_filter"))
        self.tag_filter_combo.model().item(0).setEnabled(False)
        self.tag_filter_combo.model().item(0).setForeground(QColor("#999999"))

        for tag in sorted(tags, key=str.lower):
            self.tag_filter_combo.addItem(tag)
        self.tag_filter_combo.blockSignals(False)

    def filter_by_selected_tag(self, selected_tag):
        selected = selected_tag.strip()
        if not selected or selected == self.t("select_tag_filter"):
            return

        from database.db import fetch_all_documents, get_metadata_for_path
        self.tree.clear()
        self.search_count_label.setText(self.t("search_results_count_label").format(count=0))
        self.search_count_label.show()

        count = 0
        for doc in fetch_all_documents():
            meta = get_metadata_for_path(doc[2]) or {}
            if selected.lower() in meta.get("tags", "").lower():
                rel_path = doc[2]
                parts = rel_path.split(os.sep)
                parent = None
                for i, part in enumerate(parts):
                    path_acc = os.sep.join(parts[:i+1])
                    if i == len(parts) - 1:
                        item = QTreeWidgetItem([part])
                        item.setData(0, Qt.UserRole, rel_path)
                        if parent:
                            parent.addChild(item)
                        else:
                            self.tree.addTopLevelItem(item)
                        count += 1
                    else:
                        existing = self.find_tree_item(part, parent)
                        if existing:
                            folder_item = existing
                        else:
                            folder_item = QTreeWidgetItem([part])
                            if parent:
                                parent.addChild(folder_item)
                            else:
                                self.tree.addTopLevelItem(folder_item)
                        parent = folder_item

        self.search_count_label.setText(self.t("search_results_count_label").format(count=count))


   
    def reposition_tag_filter_arrow(self):
        if hasattr(self, "tag_filter_arrow"):
            frame_width = self.tag_filter_combo.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
            self.tag_filter_arrow.move(
                self.tag_filter_combo.rect().right() - self.tag_filter_arrow.width() - frame_width,
                (self.tag_filter_combo.rect().height() - self.tag_filter_arrow.height()) // 2
            )

    def open_current_file_with_default_app(self):
        import os
        import sys
        import subprocess
        from pathlib import Path

        file_path = getattr(self, "previewed_file_path", None)
        if not file_path or not Path(file_path).is_file():
            return

        file_path = Path(file_path)

        if not file_path.exists() or not file_path.is_file():
            QMessageBox.warning(
                self,
                self.t("error_title"),
                self.t("error_file_not_found")
            )
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(file_path))
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(file_path)])
            else:
                from database.path_utils import _clean_env_for_subprocess
                subprocess.Popen(["xdg-open", str(file_path)], env=_clean_env_for_subprocess())
        except Exception as e:
            QMessageBox.warning(
                self,
                self.t("error_title"),
                self.t("error_open_file").format(error=str(e))
            )

    def update_file_info_label_state(self, clickable: bool):
        if clickable:
            self.file_info_label.setCursor(Qt.PointingHandCursor)
            self.file_info_label.setToolTip(self.t("tooltip_open_with_default_app"))
            self.file_info_label.setStyleSheet(
                "padding-left: 10px; font-style: italic; text-decoration: underline; color: #3366cc;"
            )
        else:
            self.file_info_label.setCursor(Qt.ArrowCursor)
            self.file_info_label.setToolTip("")
            self.file_info_label.setStyleSheet(
                "padding-left: 10px; font-style: italic;"
            )

from PySide6.QtCore import QPropertyAnimation
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from styles import get_tag_widget_style

# ──────────────────────────────────────────────────────────────────────────────
# TagPickerDialog — sélecteur de tags alphabétique avec navigation clavier
# ──────────────────────────────────────────────────────────────────────────────
class _ChipArea(QWidget):
    """
    Zone d'affichage de chips à enroulement automatique.
    Contourne les problèmes de sizeHint prématuré de QPushButton sous QLayout
    en positionnant les enfants manuellement via resizeEvent.
    """
    _SPACING = 8
    _MARGIN  = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips: list = []          # [(widget, w, h), ...]

    def add_chip(self, widget: QWidget):
        widget.setParent(self)
        widget.show()
        # Utiliser la taille déjà fixée (setFixedSize appelé avant add_chip)
        # widget.size() est fiable car setFixedSize → resize() est synchrone
        sz = widget.size()
        w  = sz.width()  if sz.width()  > 4 else 80
        h  = sz.height() if sz.height() > 4 else 26
        self._chips.append((widget, w, h))
        self._relayout()
        self.updateGeometry()

    def clear_chips(self):
        for widget, _, __ in self._chips:
            widget.hide()
            widget.deleteLater()
        self._chips.clear()
        self.setMinimumHeight(self._MARGIN * 2)
        self.updateGeometry()

    def chip_count(self) -> int:
        return len(self._chips)

    def chip_widgets(self):
        return [w for w, _, __ in self._chips]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        avail = max(self.width() - self._MARGIN * 2, 80)
        x = self._MARGIN
        y = self._MARGIN
        row_h = 0
        for widget, w, h in self._chips:
            if x + w > avail + self._MARGIN and x > self._MARGIN:
                x  = self._MARGIN
                y += row_h + self._SPACING
                row_h = 0
            widget.setGeometry(x, y, w, h)
            x    += w + self._SPACING
            row_h = max(row_h, h)
        self.setMinimumHeight(y + row_h + self._MARGIN)

    def sizeHint(self):
        # Calculer la hauteur pour la largeur actuelle
        avail = max(self.width() - self._MARGIN * 2, 80)
        x = self._MARGIN
        y = self._MARGIN
        row_h = 0
        for _, w, h in self._chips:
            if x + w > avail + self._MARGIN and x > self._MARGIN:
                x  = self._MARGIN
                y += row_h + self._SPACING
                row_h = 0
            x    += w + self._SPACING
            row_h = max(row_h, h)
        total_h = y + row_h + self._MARGIN
        return QSize(self.width(), max(total_h, 40))


class TagPickerDialog(QDialog):
    """
    Gestionnaire de tags.
    • Barre A–Z : filtre les chips par lettre initiale
    • Navigation clavier : taper une lettre filtre ; la retaper cycle entre les tags
    • Clic / Entrée : sélectionne ou désélectionne un tag
    • Barre basse : tags actifs avec bouton × pour retirer
    • AJOUTER / RENOMMER / SUPPRIMER : gestion globale des tags
    """

    # Couleurs gérées par tag_color() au niveau module (déterministe, stable entre sessions)

    def __init__(self, current_tags: list, all_tags: list,
                 translate_fn, theme: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionnaire de tags")
        self.setMinimumSize(700, 460)
        self.setModal(True)

        self.current_tags: list = list(current_tags)
        self.all_tags:     list = sorted(set(all_tags), key=str.casefold)
        self.t             = translate_fn
        self.theme         = theme

        self._active_letter: str  = ""
        self._cycle_list:    list = []
        self._cycle_index:   int  = -1
        self._last_clicked_tag: str | None = None   # dernier chip cliqué (pour Renommer/Supprimer)

        self.pending_rename:  tuple | None = None
        self.pending_deletes: list         = []

        self._grid_btns: dict = {}   # tag → QPushButton

        self._build_ui()
        self._filter_by_letter("")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _chip_color(self, t: str) -> str:
        return tag_color(t)

    def _chip_style(self, color: str, selected: bool) -> str:
        if selected:
            return (
                f"QPushButton {{ background: {color}; color: #fff;"
                f"  border: 2px solid {color}; border-radius: 11px;"
                f"  padding: 3px 10px; font-size: 12px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: {color}; color: #fff; border: 2px solid {color}; }}"
            )
        # Non sélectionné → contour coloré, transparent
        # Hover → fond plein coloré + texte blanc (lisible en thème clair et sombre)
        return (
            f"QPushButton {{ background: transparent; color: {color};"
            f"  border: 2px solid {color}; border-radius: 11px;"
            f"  padding: 3px 10px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {color}; color: #fff; border: 2px solid {color}; }}"
        )

    def _chip_size(self, text: str) -> tuple:
        """
        Calcule (w, h) d'un chip via QFontMetrics — aucune dépendance au sizeHint
        de QPushButton (qui est faux avant le premier rendu avec un stylesheet).
        """
        from PySide6.QtGui import QFont, QFontMetrics
        f = QFont(self.font())
        f.setPixelSize(13)          # ~ font-size: 12px du stylesheet
        fm = QFontMetrics(f)
        # padding CSS : left 10 + right 10 + 2 borders de 2px = 24
        return (max(fm.horizontalAdvance(text) + 28, 52), 28)

    def _make_chip_btn(self, tag: str, is_sel: bool) -> QPushButton:
        """Crée un QPushButton-chip avec taille explicite."""
        color = self._chip_color(tag)
        label = ("✓  " if is_sel else "") + tag
        btn   = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(is_sel)
        btn.setStyleSheet(self._chip_style(color, is_sel))
        w, h = self._chip_size(label)
        btn.setFixedSize(w, h)

        def _on_click(chk, t=tag):
            self._last_clicked_tag = t   # mémoriser avant le toggle
            self._toggle_tag(t, chk)

        btn.clicked.connect(_on_click)
        return btn

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        from styles import THEMES
        p = THEMES.get(self.theme, THEMES["light"])

        self.setStyleSheet(f"""
            QDialog     {{ background: {p["bg"]}; color: {p["text"]}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QLabel       {{ color: {p["text"]}; background: transparent; }}
            QScrollBar:vertical   {{ width: 6px; background: {p["surface2"]}; border-radius: 3px; }}
            QScrollBar::handle:vertical {{ background: {p["border"]}; border-radius: 3px; }}
        """)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(14, 14, 14, 14)

        # ── Barre alphabet ──────────────────────────────────────────────────
        alpha_bar = QWidget()
        alpha_bar.setStyleSheet(
            f"background: {p['surface2']}; border-radius: 8px;"
            f"border: 1px solid {p['border']};"
        )
        al = QHBoxLayout(alpha_bar)
        al.setContentsMargins(6, 4, 6, 4)
        al.setSpacing(2)

        alpha_style = (
            f"QPushButton {{ background: transparent; color: {p['text']};"
            f"  border: none; border-radius: 5px;"
            f"  min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px;"
            f"  font-weight: bold; font-size: 11px; padding: 0; }}"
            f"QPushButton:hover   {{ background: {p['hover']}; }}"
            f"QPushButton:checked {{ background: {p['accent']}; color: #fff; }}"
        )

        self._alpha_btns: dict = {}
        b_all = QPushButton("*")
        b_all.setCheckable(True); b_all.setChecked(True)
        b_all.setStyleSheet(alpha_style)
        b_all.clicked.connect(lambda: self._filter_by_letter(""))
        self._alpha_btns[""] = b_all
        al.addWidget(b_all)

        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            b = QPushButton(ch)
            b.setCheckable(True)
            b.setStyleSheet(alpha_style)
            b.clicked.connect(lambda _, c=ch: self._filter_by_letter(c))
            self._alpha_btns[ch] = b
            al.addWidget(b)

        al.addStretch()
        root.addWidget(alpha_bar)

        # ── Zone centrale : chips + boutons ────────────────────────────────
        centre = QHBoxLayout()
        centre.setSpacing(12)

        self._chip_scroll = QScrollArea()
        self._chip_scroll.setWidgetResizable(True)
        self._chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._chip_bg = QWidget()
        self._chip_bg.setStyleSheet(
            f"background: {p['surface']}; border: 1px solid {p['border']};"
            f"border-radius: 8px;"
        )
        bg_layout = QVBoxLayout(self._chip_bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)

        self._chip_area = _ChipArea()
        self._chip_area.setStyleSheet("background: transparent; border: none;")
        bg_layout.addWidget(self._chip_area, 0, Qt.AlignTop)
        bg_layout.addStretch()

        self._chip_scroll.setWidget(self._chip_bg)
        centre.addWidget(self._chip_scroll, 1)

        # Boutons action
        action_col = QVBoxLayout()
        action_col.setSpacing(8)

        def _darken(hex_color: str, factor: float = 0.82) -> str:
            """Assombrit une couleur hex de `factor` (0.82 = -18%)."""
            c = hex_color.lstrip("#")
            r = int(int(c[0:2], 16) * factor)
            g = int(int(c[2:4], 16) * factor)
            b = int(int(c[4:6], 16) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"

        def _abtn(label: str, color: str) -> QPushButton:
            darker  = _darken(color, 0.82)
            darkest = _darken(color, 0.68)
            b = QPushButton(label)
            b.setFixedWidth(120)
            b.setStyleSheet(
                f"QPushButton {{ background: {color}; color: #fff; border: none;"
                f"  border-radius: 7px; padding: 7px 4px; font-weight: 700;"
                f"  font-size: 12px; letter-spacing: 0.5px; }}"
                f"QPushButton:hover   {{ background: {darker};  color: #fff; border: none; }}"
                f"QPushButton:pressed {{ background: {darkest}; color: #fff; border: none; }}"
            )
            return b

        self.btn_add_new  = _abtn("AJOUTER",     "#28a745")
        self.btn_rename   = _abtn("RENOMMER",    "#007BFF")
        self.btn_del_glob = _abtn("SUPPRIMER",   "#dc3545")
        self.btn_ok       = _abtn("ENREGISTRER", p["accent"])

        self.btn_add_new.clicked.connect(self._on_add_new)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_del_glob.clicked.connect(self._on_delete_global)
        self.btn_ok.clicked.connect(self.accept)

        action_col.addWidget(self.btn_add_new)
        action_col.addWidget(self.btn_rename)
        action_col.addWidget(self.btn_del_glob)
        action_col.addStretch()
        action_col.addWidget(self.btn_ok)
        centre.addLayout(action_col)

        root.addLayout(centre, 1)

        # ── Barre basse ─────────────────────────────────────────────────────
        sel_frame = QFrame()
        sel_frame.setStyleSheet(
            f"QFrame {{ background: {p['surface2']}; border-radius: 8px;"
            f"  border: 1px solid {p['border']}; }}"
        )
        sel_frame.setFixedHeight(50)

        sel_outer = QHBoxLayout(sel_frame)
        sel_outer.setContentsMargins(8, 5, 8, 5)
        sel_outer.setSpacing(6)

        lbl_sel = QLabel("Tags :")
        lbl_sel.setStyleSheet(
            f"color: {p['text_secondary']}; font-size: 11px;"
            "background: transparent; border: none; min-width: 38px;"
        )
        sel_outer.addWidget(lbl_sel)

        self._sel_scroll = QScrollArea()
        self._sel_scroll.setWidgetResizable(True)
        self._sel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._sel_scroll.setFrameShape(QFrame.NoFrame)
        self._sel_scroll.setStyleSheet("background: transparent; border: none;")

        self._sel_widget = QWidget()
        self._sel_widget.setStyleSheet("background: transparent;")
        self._sel_layout = QHBoxLayout(self._sel_widget)
        self._sel_layout.setContentsMargins(0, 2, 0, 2)
        self._sel_layout.setSpacing(6)
        self._sel_layout.addStretch()
        self._sel_scroll.setWidget(self._sel_widget)

        sel_outer.addWidget(self._sel_scroll, 1)
        root.addWidget(sel_frame)

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _filter_by_letter(self, letter: str):
        for ch, btn in self._alpha_btns.items():
            btn.setChecked(ch == letter)
        self._active_letter = letter
        self._cycle_list    = []
        self._cycle_index   = -1
        self._repopulate_chips(letter)

    def _repopulate_chips(self, letter: str):
        self._chip_area.clear_chips()
        self._grid_btns.clear()

        tags = (
            [t for t in self.all_tags if t.casefold().startswith(letter.casefold())]
            if letter else list(self.all_tags)
        )

        if not tags:
            from styles import THEMES
            p = THEMES.get(self.theme, THEMES["light"])
            lbl = QLabel(
                "  Aucun tag pour cette lettre" if letter
                else "  Aucun tag — cliquez sur AJOUTER"
            )
            lbl.setStyleSheet(
                f"color: {p['text_secondary']}; font-style: italic;"
                "padding: 12px; background: transparent; border: none;"
            )
            self._chip_area.add_chip(lbl)
            self._cycle_list = []
            self._refresh_selected_bar()
            return

        for tag in tags:
            is_sel = any(t.casefold() == tag.casefold() for t in self.current_tags)
            btn = self._make_chip_btn(tag, is_sel)  # setFixedSize déjà appelé
            self._chip_area.add_chip(btn)
            self._grid_btns[tag] = btn

        self._cycle_list = tags
        self._refresh_selected_bar()

    def _update_chip(self, tag: str):
        """Met à jour l'apparence d'un chip après toggle (sans reconstruire toute la zone)."""
        btn = self._grid_btns.get(tag)
        if btn is None:
            return
        is_sel = any(t.casefold() == tag.casefold() for t in self.current_tags)
        color  = self._chip_color(tag)
        label  = ("✓  " if is_sel else "") + tag
        btn.setChecked(is_sel)
        btn.setText(label)
        btn.setStyleSheet(self._chip_style(color, is_sel))
        w, h = self._chip_size(label)
        btn.setFixedSize(w, h)
        # Mettre à jour la taille stockée dans _chip_area
        chips = self._chip_area._chips
        idx = next((i for i, (wgt, _, __) in enumerate(chips) if wgt is btn), None)
        if idx is not None:
            chips[idx] = (btn, w, h)
        self._chip_area._relayout()

    # ── Tag toggle & selected bar ─────────────────────────────────────────────

    def _toggle_tag(self, tag: str, add: bool):
        if add:
            if not any(t.casefold() == tag.casefold() for t in self.current_tags):
                self.current_tags.append(tag)
        else:
            self.current_tags = [t for t in self.current_tags
                                 if t.casefold() != tag.casefold()]
        self._update_chip(tag)
        self._refresh_selected_bar()

    def _refresh_selected_bar(self):
        while self._sel_layout.count():
            item = self._sel_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for tag in self.current_tags:
            color = self._chip_color(tag)
            pill  = QWidget()
            pill.setStyleSheet(
                f"background: {color}; border-radius: 10px; border: none;"
            )
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(8, 2, 4, 2)
            pl.setSpacing(3)

            lbl = QLabel(tag)
            lbl.setStyleSheet(
                "color: white; font-size: 11px; font-weight: 600;"
                "background: transparent; border: none;"
            )
            lbl.setToolTip(tag)

            rm = QPushButton("×")
            rm.setFixedSize(16, 16)
            rm.setStyleSheet(
                "QPushButton { background: transparent; color: white; border: none;"
                "  font-size: 14px; font-weight: bold; padding: 0; }"
                "QPushButton:hover { color: #ffcccc; }"
            )
            rm.clicked.connect(lambda _, t=tag: self._remove_tag(t))

            pl.addWidget(lbl)
            pl.addWidget(rm)
            self._sel_layout.addWidget(pill)

        self._sel_layout.addStretch()

    def _remove_tag(self, tag: str):
        self.current_tags = [t for t in self.current_tags
                             if t.casefold() != tag.casefold()]
        self._update_chip(tag)
        self._refresh_selected_bar()

    # ── Action buttons ────────────────────────────────────────────────────────

    def _on_add_new(self):
        text, ok = QInputDialog.getText(self, "Nouveau tag", "Nom du tag :")
        if not ok or not text.strip():
            return
        tag = text.strip()
        if not any(t.casefold() == tag.casefold() for t in self.all_tags):
            self.all_tags.append(tag)
            self.all_tags.sort(key=str.casefold)
        if not any(t.casefold() == tag.casefold() for t in self.current_tags):
            self.current_tags.append(tag)
        self._filter_by_letter(self._active_letter)

    def _on_rename(self):
        focused = self._focused_chip_tag()
        if not focused:
            QMessageBox.information(self, "Renommer",
                "Cliquez d'abord sur un tag dans la liste pour le cibler.")
            return
        new_name, ok = QInputDialog.getText(
            self, "Renommer le tag",
            f"Nouveau nom pour \u00ab {focused} \u00bb :", text=focused)
        if not ok or not new_name.strip() or new_name.strip() == focused:
            return
        new_name = new_name.strip()
        self.all_tags     = [new_name if t.casefold() == focused.casefold() else t
                             for t in self.all_tags]
        self.current_tags = [new_name if t.casefold() == focused.casefold() else t
                              for t in self.current_tags]
        self.pending_rename = (focused, new_name)
        self._last_clicked_tag = None
        QMessageBox.information(self, "Renommer",
            f"Le tag \u00ab {focused} \u00bb sera renomm\u00e9 en \u00ab {new_name} \u00bb\n"
            "sur tous les documents lors de l'enregistrement.")
        self._filter_by_letter(self._active_letter)

    def _on_delete_global(self):
        focused = self._focused_chip_tag()
        if not focused:
            QMessageBox.information(self, "Supprimer",
                "Cliquez d'abord sur un tag dans la liste pour le cibler.")
            return
        reply = QMessageBox.question(
            self, "Supprimer le tag",
            f"Supprimer \u00ab {focused} \u00bb de TOUS les documents ?\n"
            "Cette op\u00e9ration est irr\u00e9versible.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.all_tags     = [t for t in self.all_tags
                             if t.casefold() != focused.casefold()]
        self.current_tags = [t for t in self.current_tags
                             if t.casefold() != focused.casefold()]
        self.pending_deletes.append(focused)
        self._last_clicked_tag = None
        self._filter_by_letter(self._active_letter)

    def _focused_chip_tag(self) -> str | None:
        # Priorité 1 : dernier chip cliqué (clic souris)
        if self._last_clicked_tag and self._last_clicked_tag in self._grid_btns:
            return self._last_clicked_tag
        # Priorité 2 : focus clavier
        for tag, btn in self._grid_btns.items():
            if btn.hasFocus():
                return tag
        # Priorité 3 : position du cycle clavier
        if self._cycle_list and 0 <= self._cycle_index < len(self._cycle_list):
            return self._cycle_list[self._cycle_index]
        return None

    # ── Keyboard navigation ───────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key_text = event.text().upper()

        if key_text and key_text in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if key_text == self._active_letter and self._cycle_list:
                self._cycle_index = (self._cycle_index + 1) % len(self._cycle_list)
                target = self._cycle_list[self._cycle_index]
                if target in self._grid_btns:
                    self._grid_btns[target].setFocus()
            else:
                self._filter_by_letter(key_text)
                if self._cycle_list:
                    self._cycle_index = 0
                    if self._cycle_list[0] in self._grid_btns:
                        self._grid_btns[self._cycle_list[0]].setFocus()

        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            for tag, btn in self._grid_btns.items():
                if btn.hasFocus():
                    self._toggle_tag(tag, not btn.isChecked())
                    if self._cycle_list and self._cycle_index < len(self._cycle_list) - 1:
                        self._cycle_index += 1
                        nxt = self._cycle_list[self._cycle_index]
                        if nxt in self._grid_btns:
                            self._grid_btns[nxt].setFocus()
                    break

        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class TagWidget(QFrame):
    def __init__(self, text, remove_callback):
        super().__init__()
        self.text = text
        self.remove_callback = remove_callback
        self.setObjectName("TagWidget")

        self.setStyleSheet(get_tag_widget_style())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        self.label = QLabel(text)
        self.label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.remove_button = QPushButton("Ã—")
        self.remove_button.setObjectName("tagRemoveButton")
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setFixedSize(18, 18)
        self.remove_button.clicked.connect(self.animate_removal)

        layout.addWidget(self.label)
        layout.addWidget(self.remove_button)

        # Calcul dynamique de la largeur *après* création du label
        # font_metrics = QFontMetrics(self.label.font())
        # text_width = font_metrics.horizontalAdvance(text)
        # total_width = text_width + self.remove_button.width() + 24  # marge + padding

        # Ã‰vite les tags démesurés mais laisse respirer
        # self.setMaximumWidth(min(200, total_width))
        # self.setMinimumWidth(total_width)

    def animate_removal(self):
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)

        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.delete_tag)
        self.animation.start()

    def delete_tag(self):
        self.remove_callback(self)
        self.setParent(None)
        self.deleteLater()

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import QTimer, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QFontMetrics, QLinearGradient, QColor, QBrush, QCursor

from PySide6.QtCore import Signal

class ScrollingItemDelegate(QStyledItemDelegate):
    def __init__(self, tree_widget, accent_color: str = "#007BFF"):
        super().__init__(tree_widget)
        self.tree_widget = tree_widget
        self.accent_color = accent_color
        self.scroll_offset = 0
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.update_scroll)
        self.hovered_index = None
        self.scroll_speed = 2

        self.tree_widget_deleted = False
        self.tree_widget.destroyed.connect(self.on_widget_deleted)
        tree_widget.viewport().installEventFilter(self)
        tree_widget.setMouseTracking(True)

    def eventFilter(self, obj, event):
        # Si l'objet QTreeWidget a été supprimé, on ne traite plus l'événement
        if self.tree_widget_deleted:
            return super().eventFilter(obj, event)

        if obj is self.tree_widget.viewport():
            pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
            index = self.tree_widget.indexAt(pos)

            if index != self.hovered_index:
                self.hovered_index = index
                self.scroll_offset = 0
                if index.isValid():
                    self.scroll_timer.start(40)
                else:
                    self.scroll_timer.stop()
                self.tree_widget.viewport().update()

        return super().eventFilter(obj, event)

    def on_widget_deleted(self):
        """Cette méthode est appelée lorsque tree_widget est supprimé ou nettoyé."""
        self.tree_widget_deleted = True

    def update_scroll(self):
        if not self.hovered_index or not self.hovered_index.isValid():
            self.scroll_timer.stop()
            return

        text = self.hovered_index.data()
        if not text:
            return

        fm = QFontMetrics(self.tree_widget.font())
        text_width = fm.horizontalAdvance(text)
        rect = self.tree_widget.visualRect(self.hovered_index)
        icon_space = 24 + 8
        available_width = rect.width() - icon_space

        if text_width <= available_width:
            self.scroll_offset = 0
            return

        self.scroll_offset += self.scroll_speed
        if self.scroll_offset > text_width:
            self.scroll_offset = 0

        self.tree_widget.viewport().update(rect)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        text = index.data()
        if not text:
            painter.restore()
            return

        rect        = option.rect
        icon        = index.model().data(index, Qt.DecorationRole)
        fm          = QFontMetrics(option.font)
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered  = (index == self.hovered_index) and not is_selected

        accent = QColor(self.accent_color)

        # Fond et indicateur gauche
        bg_rect = QRectF(rect).adjusted(3, 1, -3, -1)

        if is_selected:
            # Fond pleine largeur en accent très transparent
            bg = QColor(accent); bg.setAlpha(22)
            painter.setBrush(bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bg_rect, 6, 6)
            # Barre verticale gauche accent opaque (4 px)
            painter.setBrush(accent)
            bar_rect = QRectF(rect.left() + 3, rect.top() + 5, 4, rect.height() - 10)
            painter.drawRoundedRect(bar_rect, 2, 2)
            text_color = accent

        elif is_hovered:
            bg = QColor(accent); bg.setAlpha(12)
            painter.setBrush(bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bg_rect, 6, 6)
            text_color = option.palette.text().color()
        else:
            text_color = option.palette.text().color()

        # Icone
        icon_size = 22
        icon_x    = rect.left() + 14
        icon_rect = QRectF(icon_x, rect.top() + (rect.height() - icon_size) / 2,
                           icon_size, icon_size)
        text_x = icon_rect.right() + 5

        if isinstance(icon, QIcon):
            icon.paint(painter, int(icon_rect.left()), int(icon_rect.top()),
                       icon_size, icon_size)

        # Texte (defilant si trop long)
        text_width      = fm.horizontalAdvance(text)
        available_width = rect.right() - text_x - 8
        text_y = rect.top() + (rect.height() + fm.ascent() - fm.descent()) / 2

        if is_selected:
            font = option.font
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)

        painter.setPen(text_color)

        if index == self.hovered_index and text_width > available_width:
            painter.setClipRect(QRectF(text_x, rect.top(), available_width, rect.height()))
            painter.drawText(QPointF(text_x - self.scroll_offset, text_y), text)
            bg_base = option.palette.base().color()
            c0 = QColor(bg_base); c0.setAlpha(240)
            c1 = QColor(bg_base); c1.setAlpha(0)
            grad_l = QLinearGradient(text_x, 0, text_x + 20, 0)
            grad_l.setColorAt(0, c0); grad_l.setColorAt(1, c1)
            painter.fillRect(QRectF(text_x, rect.top(), 20, rect.height()), QBrush(grad_l))
            grad_r = QLinearGradient(text_x + available_width - 20, 0, text_x + available_width, 0)
            grad_r.setColorAt(0, c1); grad_r.setColorAt(1, c0)
            painter.fillRect(QRectF(text_x + available_width - 20, rect.top(), 20, rect.height()), QBrush(grad_r))
        else:
            painter.drawText(QPointF(text_x, text_y), text)

        painter.restore()

from PySide6.QtCore import QObject, Signal
import sys
from pathlib import Path

class BackupWorker(QObject):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, files_dir, db_path, save_path, translations, current_language):
        super().__init__()

        self.translations = translations  # Ajout de l'attribut translations
        self.current_language = current_language  # Ajout de l'attribut current_language

        # Utiliser les chemins définis dans config.py
        self.db_path = db_path if not hasattr(sys, '_MEIPASS') else config.DB_PATH  # Utilise config.DB_PATH
        self.files_dir = files_dir if not hasattr(sys, '_MEIPASS') else config.FILES_DIR  # Utilise config.FILES_DIR
        self.save_path = save_path

    def run(self):
        import zipfile, os
        try:
            total_items = sum(len(files) for _, _, files in os.walk(self.files_dir)) + 1  # +1 pour la base
            processed = 0

            with zipfile.ZipFile(self.save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.files_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, os.path.dirname(self.files_dir))

                        if os.path.islink(full_path):
                            target = os.readlink(full_path)
                            info = zipfile.ZipInfo(rel_path)
                            info.create_system = 3  # Unix
                            info.external_attr = 0o120777 << 16  # Type fichier : symlink
                            zipf.writestr(info, target.encode('utf-8'))
                        else:
                            zipf.write(full_path, arcname=rel_path)

                        processed += 1
                        self.progress.emit(int(processed * 100 / total_items))

                # Sauvegarde de la base de données
                zipf.write(self.db_path, arcname="ged.db")
                processed += 1
                self.progress.emit(int(processed * 100 / total_items))

            msg = self.translations.get(self.current_language, {}).get(
                "backup_done_message", "Sauvegarde terminée."
            )
            self.finished.emit(msg)

        except Exception as e:
            self.error.emit(str(e))

class RestoreWorker(QObject):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, zip_path, files_dir, db_path, translations, current_language):
        super().__init__()
        self.zip_path = zip_path
        self.files_dir = files_dir
        self.db_path = db_path
        self.translations = translations
        self.current_language = current_language

    def run(self):
        import zipfile, shutil, os
        from pathlib import Path
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zipf:
                namelist = zipf.namelist()
                total = len(namelist)
                count = 0

                # Purge les anciens fichiers
                if os.path.exists(self.files_dir):
                    shutil.rmtree(self.files_dir)
                os.makedirs(self.files_dir, exist_ok=True)

                for name in namelist:
                    member = zipf.getinfo(name)
                    target_path = Path(self.files_dir).parent / name

                    # Création des sous-dossiers
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    if name == "ged.db":
                        # Base SQLite â†’ copie directe dans db_path
                        with open(self.db_path, 'wb') as out_db:
                            out_db.write(zipf.read(name))
                    elif (member.external_attr >> 16) & 0o170000 == 0o120000:
                        # C'est un lien symbolique
                        target = zipf.read(name).decode('utf-8')
                        target_path_obj = Path(target)
                        is_dir_symlink = target_path_obj.is_dir() if target_path_obj.exists() else not bool(target_path_obj.suffix)
                        os.symlink(target, target_path, target_is_directory=is_dir_symlink)
                    else:
                        # Fichier standard
                        with open(target_path, 'wb') as f:
                            f.write(zipf.read(name))

                    count += 1
                    self.progress.emit(int(count * 100 / total))

            msg = self.translations.get(self.current_language, {}).get(
                "restore_done_message", "Restauration terminée."
            )
            self.finished.emit(msg)

        except Exception as e:
            self.error.emit(str(e))


class SearchWorker(QObject):
    result_found = Signal(tuple)
    progress     = Signal(int, int)  # val, total
    finished     = Signal()
    error        = Signal(str)

    def __init__(self, keywords, translate):
        super().__init__()
        # Normalisation en minuscules dès le départ
        self.keywords  = [kw.lower() for kw in keywords]
        self.translate = translate
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            all_docs = fetch_all_documents()
            total    = len(all_docs)

            for i, doc in enumerate(all_docs):
                if not self._is_running:
                    break

                rel_path = doc[2]
                filename = Path(rel_path).name.lower()
                abs_path = config.FILES_DIR / rel_path

                # On teste nom et métadonnées quoi quâ€™il arrive
                found = True
                for kw in self.keywords:
                    in_name     = kw in filename
                    in_metadata = matches_metadata(rel_path, [kw])

                    # Recherche dans le contenu **seulement** si le fichier existe
                    in_content = False
                    if abs_path.exists():
                        in_content = matches_content(abs_path, kw, self.translate)

                    if not (in_name or in_metadata or in_content):
                        found = False
                        break

                if found:
                    self.result_found.emit(doc)

                self.progress.emit(i+1, total)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()



from PySide6.QtWidgets import QLayout, QSizePolicy, QWidgetItem
from PySide6.QtCore import QSize, Qt, QPoint, QRect

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def removeWidget(self, widget):
        """Supprime un widget de manière sécurisée du layout."""
        for i, item in enumerate(self.item_list):
            if item.widget() == widget:
                self.item_list.pop(i)
                break

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QPoint(0, 0), width, test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect.topLeft(), rect.width())

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        # Calculer la hauteur réelle en fonction de la largeur disponible
        parent = self.parentWidget()
        if parent and parent.width() > 0:
            h = self._do_layout(QPoint(0, 0), parent.width(), test_only=True)
        else:
            # Fallback : hauteur pour 1 ligne de tags
            max_item_h = 0
            for item in self.item_list:
                max_item_h = max(max_item_h, item.minimumSize().height())
            h = max(max_item_h, 32)
        margins = self.contentsMargins()
        return QSize(50, h + margins.top() + margins.bottom())

    def _do_layout(self, position, width, test_only=False):
        x, y = position.x(), position.y()
        line_height = 0
        for item in self.item_list:
            widget = item.widget()
            if widget is None or not widget.isVisible():
                continue
            space_x = self.spacing()
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > position.x() + width and line_height > 0:
                x = position.x()
                y += line_height + self.spacing()
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - position.y()


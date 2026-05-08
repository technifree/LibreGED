# folder_browser.py — LibreGED
# Widget de navigation de dossiers (style explorateur de fichiers)
# À placer dans le même répertoire que main_window.py

import os
import sys
from pathlib import Path

def _is_symlink(path) -> bool:
    """
    Détection robuste des liens symboliques sur Windows et Linux.
    Sur Windows, os.path.islink() détecte aussi les jonctions NTFS.
    Path.is_symlink() ne détecte pas toujours les jonctions Windows.
    """
    try:
        return os.path.islink(str(path))
    except (OSError, ValueError):
        return False

def _resolve_safe(path) -> str:
    """Résout le lien symbolique sans crasher sur Windows."""
    try:
        return str(Path(str(path)).resolve())
    except (OSError, ValueError, RuntimeError):
        try:
            return os.readlink(str(path))
        except (OSError, AttributeError):
            return str(path)

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, Signal, QObject, QThread, QRect, QPoint
from PySide6.QtGui import QColor, QFont, QCursor, QPixmap, QPainter, QIcon, QBrush, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QFrame, QToolButton, QApplication,
    QLayout, QWidgetItem, QListWidget, QListWidgetItem
)

# ---------------------------------------------------------------------------
# FlowLayout — copie autonome (évite l'import circulaire depuis main_window)
# ---------------------------------------------------------------------------
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
        from PySide6.QtCore import QSize as _QSize
        size = _QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins().top()
        size += _QSize(2 * m, 2 * m)
        return size

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

# ---------------------------------------------------------------------------
# Palette de couleurs par thème
# ---------------------------------------------------------------------------
# Thèmes sombres — mappés sur la palette "dark" du browser
_DARK_THEMES = {"dark", "twilight", "ocean", "forest", "sunset",
                "rose", "slate", "midnight", "brown"}

def _build_theme_colors():
    """Génère THEME_COLORS pour tous les thèmes depuis styles.THEMES."""
    try:
        from styles import THEMES
    except ImportError:
        THEMES = {}

    # Palettes spécifiques au FolderBrowser pour light et dark
    base = {
        "dark": {
            "bg":          "#1e1e2e",
            "item_bg":     "#2a2a3e",
            "item_hover":  "#3a3a5c",
            "item_border": "#44446a",
            "text":        "#e0e0f0",
            "text_dim":    "#8888aa",
            "nav_bg":      "#16162a",
            "nav_border":  "#333355",
            "folder":      "#5599ff",
            "accent":      "#0078D7",
            "back_btn_bg": "#2a2a3e",
            "breadcrumb":  "#7799cc",
        },
        "light": {
            "bg":          "#f4f6fb",
            "item_bg":     "#ffffff",
            "item_hover":  "#e8f0fe",
            "item_border": "#d0d8e8",
            "text":        "#1a1a2e",
            "text_dim":    "#5566aa",
            "nav_bg":      "#eaecf5",
            "nav_border":  "#c8cce0",
            "folder":      "#0057c2",
            "accent":      "#0078D7",
            "back_btn_bg": "#dde3f0",
            "breadcrumb":  "#0057c2",
        },
    }

    result = dict(base)

    # Pour chaque thème de styles.THEMES, construire une palette dérivée
    for theme_key, t in THEMES.items():
        if theme_key in base:
            continue  # déjà défini
        is_dark = theme_key in _DARK_THEMES
        result[theme_key] = {
            "bg":          t["bg"],
            "item_bg":     t["surface"],
            "item_hover":  t["hover"],
            "item_border": t["border"],
            "text":        t["text"],
            "text_dim":    t["text_secondary"],
            "nav_bg":      t["surface2"],
            "nav_border":  t["border"],
            "folder":      t["accent"],
            "accent":      t["accent"],
            "back_btn_bg": t["surface2"],
            "breadcrumb":  t["accent"],
        }

    return result


THEME_COLORS = _build_theme_colors()


def _resolve_theme(theme: str) -> dict:
    """Retourne la palette pour un thème, avec fallback sur dark/light."""
    if theme in THEME_COLORS:
        return THEME_COLORS[theme]
    # Fallback : dark si thème sombre inconnu, sinon light
    fallback = "dark" if theme in _DARK_THEMES else "light"
    return THEME_COLORS[fallback]

# Icônes qtawesome par extension
EXT_ICONS = {
    ".pdf":  ("fa5s.file-pdf",   "#e74c3c"),
    ".txt":  ("fa5s.file-alt",   "#888888"),
    ".md":   ("fa5s.file-alt",   "#888888"),
    ".py":   ("fa5s.file-code",  "#3498db"),
    ".html": ("fa5s.file-code",  "#e67e22"),
    ".htm":  ("fa5s.file-code",  "#e67e22"),
    ".jpg":  ("fa5s.file-image", "#27ae60"),
    ".jpeg": ("fa5s.file-image", "#27ae60"),
    ".png":  ("fa5s.file-image", "#27ae60"),
    ".gif":  ("fa5s.file-image", "#27ae60"),
    ".bmp":  ("fa5s.file-image", "#27ae60"),
    ".tif":  ("fa5s.file-image", "#27ae60"),
    ".tiff": ("fa5s.file-image", "#27ae60"),
    ".docx": ("fa5s.file-word",  "#2980b9"),
    ".doc":  ("fa5s.file-word",  "#2980b9"),
    ".xlsx": ("fa5s.file-excel", "#27ae60"),
    ".xlsm": ("fa5s.file-excel", "#27ae60"),
    ".pptx": ("fa5s.file-powerpoint", "#e74c3c"),
    ".odt":  ("fa5s.file-alt",   "#f39c12"),
    ".ods":  ("fa5s.file-alt",   "#f39c12"),
    ".odp":  ("fa5s.file-alt",   "#f39c12"),
    ".epub": ("fa5s.book",       "#8e44ad"),
    ".zip":  ("fa5s.file-archive", "#795548"),
    ".tar":  ("fa5s.file-archive", "#795548"),
    ".gz":   ("fa5s.file-archive", "#795548"),
}


def _icon_for_ext(ext: str):
    """Retourne (icon_name, color) pour l'extension donnée."""
    return EXT_ICONS.get(ext.lower(), ("fa5s.file", "#607d8b"))


# ---------------------------------------------------------------------------
# Badge lien symbolique
# ---------------------------------------------------------------------------
def _make_symlink_icon(base_icon: QIcon, size: int = 52) -> QIcon:
    """
    Superpose un petit badge flèche en bas à gauche.
    Robuste : gère les pixmaps null sur Windows.
    """
    try:
        base_px = base_icon.pixmap(QSize(size, size))
        if base_px.isNull():
            return base_icon

        result = QPixmap(size, size)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        if not painter.isActive():
            return base_icon

        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, base_px)

        badge_size = max(14, size // 3)
        bx, by = 0, size - badge_size

        from PySide6.QtGui import QBrush, QPen
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#aaaaaa"), 0.5))
        painter.drawRoundedRect(bx, by, badge_size, badge_size, 3, 3)

        arrow_px = qta.icon("fa5s.external-link-alt", color="#555555").pixmap(
            QSize(badge_size - 4, badge_size - 4)
        )
        if not arrow_px.isNull():
            painter.drawPixmap(bx + 2, by + 2, arrow_px)

        painter.end()
        return QIcon(result)

    except Exception as e:
        print(f"[WARN] badge symlink : {e}")
        return base_icon


# ---------------------------------------------------------------------------
# Widget d'un item (fichier ou dossier)
# ---------------------------------------------------------------------------
class FolderItem(QFrame):
    """Un item cliquable représentant un fichier ou un dossier."""

    clicked = Signal(object)   # émet self

    def __init__(self, name: str, is_dir: bool, abs_path: Path,
                 rel_path: str, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.name = name
        self.is_dir = is_dir
        self.abs_path = abs_path
        self.rel_path = rel_path
        self.theme = theme
        self._c = _resolve_theme(theme)
        self._hovered = False

        self.setFixedSize(120, 140)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFrameShape(QFrame.StyledPanel)
        self._apply_style(hover=False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # --- Icône ---
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(56, 56)
        icon_pixmap = self._build_icon()
        self.icon_label.setPixmap(icon_pixmap)
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # --- Nom sur 2 lignes max, coupé proprement ---
        display_name = self._format_name(name)
        self.name_label = QLabel(display_name)
        self.name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedWidth(108)
        self.name_label.setMinimumHeight(34)
        self.name_label.setMaximumHeight(34)
        font = QFont()
        font.setPointSize(8)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet(f"color: {self._c['text']}; background: transparent;")
        self.name_label.setToolTip(name)
        layout.addWidget(self.name_label, 0, Qt.AlignCenter)

    # -- helpers ----------------------------------------------------------

    def _format_name(self, name: str) -> str:
        """Affiche le nom sur 2 lignes max (~16 chars/ligne).
        Si trop long, tronque avec ellipse en conservant l'extension."""
        MAX_LINE  = 16
        MAX_TOTAL = MAX_LINE * 2   # 32 chars affichables max
        if len(name) <= MAX_LINE:
            return name            # tient sur une ligne
        if len(name) <= MAX_TOTAL:
            return name            # word-wrap suffira sur 2 lignes
        # Trop long : tronquer en preservant l'extension
        stem = Path(name).stem
        ext  = Path(name).suffix
        budget = MAX_TOTAL - len(ext) - 1
        return stem[:budget] + "\u2026" + ext

    def _build_icon(self):
        size = QSize(48, 48)
        if self.is_dir:
            color = self._c["folder"]
            # Dossier lien symbolique → couleur cyan
            if _is_symlink(self.abs_path):
                color = "#00bcd4"
            icon = qta.icon("fa5s.folder", color=color)
        else:
            ext = self.abs_path.suffix
            icon_name, color = _icon_for_ext(ext)
            icon = qta.icon(icon_name, color=color)
        return icon.pixmap(size)

    def _apply_style(self, hover: bool):
        c = self._c
        bg = c["item_hover"] if hover else c["item_bg"]
        border = c["accent"] if hover else c["item_border"]
        radius = "10px"
        self.setStyleSheet(
            f"FolderItem {{ "
            f"  background-color: {bg}; "
            f"  border: 1.5px solid {border}; "
            f"  border-radius: {radius}; "
            f"}}"
        )

    # -- events -----------------------------------------------------------

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style(hover=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Générateur de miniatures (thread de fond)
# ---------------------------------------------------------------------------
THUMB_SIZE = 96  # pixels carrés pour les miniatures

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp'}
PDF_EXTS   = {'.pdf'}


def _make_thumbnail(path: Path, size: int = THUMB_SIZE) -> QPixmap | None:
    """
    Génère une miniature pour les images et PDFs.
    Retourne None si pas possible (autres types).
    Compatible Windows/Linux/PyInstaller.
    """
    ext = path.suffix.lower()

    if ext in IMAGE_EXTS:
        try:
            px = QPixmap(str(path))
            if not px.isNull():
                return px.scaled(size, size, Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
        except Exception:
            pass

    elif ext in PDF_EXTS:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            if doc.page_count > 0:
                page = doc[0]
                # Zoom pour avoir ~THUMB_SIZE px sur le plus grand côté
                zoom = size / max(page.rect.width, page.rect.height)
                mat  = fitz.Matrix(zoom, zoom)
                pix  = page.get_pixmap(matrix=mat, alpha=False)
                img  = QImage(pix.samples, pix.width, pix.height,
                              pix.stride, QImage.Format_RGB888)
                doc.close()
                return QPixmap.fromImage(img)
        except Exception:
            pass

    return None


class ThumbnailWorker(QObject):
    """Charge les miniatures en arrière-plan et les émet au fil de l'eau."""
    thumbnail_ready = Signal(str, QPixmap)  # abs_path_str, pixmap

    def __init__(self, entries: list, size: int = THUMB_SIZE):
        super().__init__()
        self._entries = entries
        self._size    = size
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        for path in self._entries:
            if not self._running:
                break
            px = _make_thumbnail(path, self._size)
            if px and not px.isNull():
                self.thumbnail_ready.emit(str(path), px)


# ---------------------------------------------------------------------------
# Widget principal : navigateur de dossier
# ---------------------------------------------------------------------------
class FolderBrowserWidget(QWidget):
    """
    Affiche le contenu d'un dossier sous forme de grille d'icônes.

    Signals
    -------
    file_activated(rel_path: str)
        Émis quand l'utilisateur clique sur un fichier.
        rel_path est relatif à files_dir.
    folder_navigated(abs_path: str)
        Émis quand l'utilisateur navigue dans un sous-dossier.
        Utile pour synchroniser le panneau gauche.
    """

    file_activated  = Signal(str)
    folder_navigated = Signal(str)
    print_requested  = Signal(str)  # rel_path du fichier à imprimer

    def __init__(self, files_dir: Path, theme: str = "dark", translate=None, parent=None):
        super().__init__(parent)
        self.files_dir = Path(files_dir)
        self.theme = theme
        self._c = _resolve_theme(theme)
        # Fonction de traduction — fallback sur l'identité si non fournie
        self._t = translate if translate is not None else (lambda k: k)

        # Navigation
        self._current_path: Path | None = None
        self._history: list[Path] = []

        # Cache miniatures : abs_path_str → QPixmap
        self._thumb_cache: dict = {}
        # Référence au thread en cours (pour l'annuler si on change de dossier)
        self._thumb_thread: QThread | None = None
        self._thumb_worker: ThumbnailWorker | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Barre de navigation ──────────────────────────────────────
        self.nav_bar = QWidget()
        self.nav_bar.setObjectName("FolderNavBar")
        self.nav_bar.setFixedHeight(52)
        self._style_nav_bar()

        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(12, 6, 12, 6)
        nav_layout.setSpacing(8)

        # Bouton Précédent
        self.back_btn = QPushButton()
        self.back_btn.setIcon(qta.icon("fa5s.arrow-left", color=self._c["accent"]))
        self.back_btn.setToolTip(self._t("folder_browser_back"))
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.setEnabled(False)
        self.back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.back_btn.setStyleSheet(
            f"QPushButton {{ background: {self._c['back_btn_bg']}; "
            f"  border: 1px solid {self._c['nav_border']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {self._c['item_hover']}; }}"
            f"QPushButton:disabled {{ opacity: 0.4; }}"
        )
        self.back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self.back_btn)

        # Breadcrumb (scrollable horizontalement)
        self.breadcrumb_scroll = QScrollArea()
        self.breadcrumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.breadcrumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.breadcrumb_scroll.setWidgetResizable(True)
        self.breadcrumb_scroll.setFrameShape(QFrame.NoFrame)
        self.breadcrumb_scroll.setStyleSheet("background: transparent;")
        self.breadcrumb_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.breadcrumb_scroll.setFixedHeight(36)

        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setStyleSheet("background: transparent;")
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(4)
        self.breadcrumb_layout.addStretch()
        self.breadcrumb_scroll.setWidget(self.breadcrumb_widget)

        nav_layout.addWidget(self.breadcrumb_scroll, 1)

        # Compteur d'items
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {self._c['text_dim']}; font-size: 11px;")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        nav_layout.addWidget(self.count_label)

        # Bouton Imprimer — visible seulement quand un fichier est sélectionné
        self.print_btn = QPushButton()
        self.print_btn.setIcon(qta.icon("fa5s.print", color=self._c["accent"]))
        self.print_btn.setToolTip("Imprimer")
        self.print_btn.setFixedSize(32, 32)
        self.print_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.print_btn.setVisible(False)
        self.print_btn.clicked.connect(self._on_print_clicked)
        self._style_print_btn()
        nav_layout.addWidget(self.print_btn)

        root_layout.addWidget(self.nav_bar)

        # ── Zone de contenu (QListWidget en mode icônes) ─────────────
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(8)
        self.list_widget.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.list_widget.setGridSize(QSize(THUMB_SIZE + 30, THUMB_SIZE + 52))
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setWordWrap(True)
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self._on_list_item_double_clicked)
        self.list_widget.itemClicked.connect(self._on_list_item_single_clicked)
        self._apply_list_style()
        root_layout.addWidget(self.list_widget, 1)

        # ── Message "dossier vide" ────────────────────────────────────
        self.empty_label = QLabel(self._t("folder_browser_empty"))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            f"color: {self._c['text_dim']}; font-size: 14px; padding: 40px;"
        )
        self.empty_label.hide()
        root_layout.addWidget(self.empty_label)

    def _style_print_btn(self):
        c = self._c
        self.print_btn.setStyleSheet(
            f"QPushButton {{ background: {c['back_btn_bg']}; "
            f"  border: 1px solid {c['nav_border']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {c['item_hover']}; }}"
        )

    def _style_nav_bar(self):
        c = self._c
        self.nav_bar.setStyleSheet(
            f"#FolderNavBar {{ "
            f"  background: {c['nav_bg']}; "
            f"  border: 1px solid {c['nav_border']}; "
            f"  border-radius: 10px; "
            f"}}"
        )

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def load_folder(self, abs_path: Path, push_history: bool = True):
        """
        Charge et affiche le contenu de abs_path.
        Si push_history est True, l'ancien dossier est empilé dans l'historique.
        """
        abs_path = Path(abs_path)
        if not abs_path.is_dir():
            return

        # Vider le cache miniatures quand on change de dossier
        if self._current_path != abs_path:
            self._thumb_cache.clear()

        if push_history and self._current_path is not None:
            self._history.append(self._current_path)

        self._current_path = abs_path
        self.back_btn.setEnabled(bool(self._history))
        self._update_breadcrumb()
        self._populate_grid()

        # Notifier le reste de l'application
        self.folder_navigated.emit(str(abs_path))

    def set_theme(self, theme: str):
        """Met à jour le thème à la volée."""
        self.theme = theme
        self._c = _resolve_theme(theme)
        self._style_nav_bar()
        self._apply_list_style()
        self.empty_label.setStyleSheet(
            f"color: {self._c['text_dim']}; font-size: 14px; padding: 40px;"
        )
        self.count_label.setStyleSheet(
            f"""
            color: {self._c['text_dim']};
            font-size: 11px;
            background: {self._c['item_bg']};
            border: 1px solid {self._c['nav_border']};
            border-radius: 8px;
            padding: 6px 10px;
            """
        )
        # Rechargement complet avec le nouveau thème
        if self._current_path:
            self._populate_grid()

    # ------------------------------------------------------------------
    # Navigation interne
    # ------------------------------------------------------------------

    def _go_back(self):
        if self._history:
            prev = self._history.pop()
            self.load_folder(prev, push_history=False)



    # ------------------------------------------------------------------
    # Construction de la grille
    # ------------------------------------------------------------------

    def _apply_list_style(self):
        """Style épuré — texte toujours visible sous la miniature."""
        c = self._c
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {c['bg']};
                border: none;
                padding: 10px;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                border-radius: 6px;
                color: {c['text']};
                font-size: 10px;
                padding: 0px;
            }}
            QListWidget::item:hover {{
                background: {c['item_hover']};
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background: {c['accent']}28;
                border-radius: 6px;
                color: {c['text']};
            }}
        """)
        from PySide6.QtGui import QFont as _QFont
        f = _QFont()
        f.setPointSize(9)
        self.list_widget.setFont(f)

    def _stop_thumb_thread(self):
        """Arrête proprement le thread de miniatures en cours."""
        if self._thumb_worker:
            self._thumb_worker.stop()
        if self._thumb_thread and self._thumb_thread.isRunning():
            self._thumb_thread.quit()
            self._thumb_thread.wait(1000)
        self._thumb_thread = None
        self._thumb_worker = None

    def _on_thumbnail_ready(self, abs_path_str: str, pixmap: QPixmap):
        """Appelé depuis le thread de miniatures : met à jour l'item."""
        self._thumb_cache[abs_path_str] = pixmap
        # Chercher l'item correspondant et mettre à jour son icône
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.UserRole + 2) == abs_path_str:
                item.setIcon(QIcon(pixmap))
                break

    def _populate_grid(self):
        """Vide et reremplit la liste avec le contenu du dossier courant."""
        self._stop_thumb_thread()
        self.list_widget.clear()
        self.print_btn.setVisible(False)

        if self._current_path is None:
            return

        # Lister le contenu : dossiers d'abord, puis fichiers, tri alpha
        try:
            entries = list(self._current_path.iterdir())
        except PermissionError:
            entries = []

        entries = [
            e for e in entries
            if not e.name.startswith(".")
            and e.name != ".keep"
            and not e.name.endswith(".json")
        ]

        dirs  = sorted([e for e in entries if e.is_dir()],  key=lambda p: p.name.lower())
        files = sorted([e for e in entries if e.is_file()], key=lambda p: p.name.lower())
        all_entries = dirs + files

        if not all_entries:
            self.empty_label.show()
            self.list_widget.hide()
        else:
            self.empty_label.hide()
            self.list_widget.show()

        # Fichiers qui auront besoin d'une miniature (pas encore en cache)
        files_for_thumb = []

        for entry in all_entries:
            try:
                rel = str(entry.relative_to(self.files_dir))
            except ValueError:
                rel = str(entry)

            is_dir     = entry.is_dir()
            is_symlink = _is_symlink(entry)

            # Icône initiale
            if is_dir:
                color = "#00bcd4" if is_symlink else self._c["folder"]
                icon  = qta.icon("fa5s.folder", color=color)
            else:
                abs_str = str(entry)
                # Miniature en cache ?
                if abs_str in self._thumb_cache:
                    cached = self._thumb_cache[abs_str]
                    icon   = QIcon(cached)
                    if is_symlink:
                        icon = _make_symlink_icon(icon, THUMB_SIZE)
                elif entry.suffix.lower() in IMAGE_EXTS | PDF_EXTS:
                    # Icône placeholder pendant le chargement
                    icon_name, color = _icon_for_ext(entry.suffix)
                    icon = qta.icon(icon_name, color=color)
                    if is_symlink:
                        icon = _make_symlink_icon(icon)
                    files_for_thumb.append(entry)
                else:
                    icon_name, color = _icon_for_ext(entry.suffix)
                    icon = qta.icon(icon_name, color=color)
                    if is_symlink:
                        icon = _make_symlink_icon(icon)

            display_name = self._format_name(entry.name)
            item = QListWidgetItem(icon, display_name)
            if is_symlink:
                item.setToolTip(f"{entry.name}\n→ {_resolve_safe(entry)}")
            else:
                item.setToolTip(entry.name)
            item.setData(Qt.UserRole,     rel)
            item.setData(Qt.UserRole + 1, is_dir)
            item.setData(Qt.UserRole + 2, str(entry))
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            item.setSizeHint(QSize(THUMB_SIZE + 30, THUMB_SIZE + 52))
            self.list_widget.addItem(item)

        # Lancer le thread de miniatures pour les fichiers qui en ont besoin
        if files_for_thumb:
            self._thumb_worker = ThumbnailWorker(files_for_thumb, THUMB_SIZE)
            self._thumb_thread = QThread()
            self._thumb_worker.moveToThread(self._thumb_thread)
            self._thumb_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
            self._thumb_thread.started.connect(self._thumb_worker.run)
            self._thumb_thread.start()

        # Compteur
        n_dirs  = len(dirs)
        n_files = len(files)
        parts = []
        if n_dirs:
            word = self._t("folder_browser_folders") if n_dirs > 1 else self._t("folder_browser_folder")
            parts.append(f"{n_dirs} {word}")
        if n_files:
            word = self._t("folder_browser_files") if n_files > 1 else self._t("folder_browser_file")
            parts.append(f"{n_files} {word}")
        self.count_label.setText("  ".join(parts))

    def _format_name(self, name: str) -> str:
        """Retourne le nom complet — Qt gère le word-wrap."""
        return name

    def _on_list_item_single_clicked(self, item: QListWidgetItem):
        """Sélection simple : affiche le bouton print si c'est un fichier."""
        if item is None:
            self.print_btn.setVisible(False)
            return
        is_dir = item.data(Qt.UserRole + 1)
        self.print_btn.setVisible(not is_dir)

    def _on_list_item_double_clicked(self, item: QListWidgetItem):
        """Double-clic : ouvrir dossier ou prévisualiser fichier."""
        is_dir   = item.data(Qt.UserRole + 1)
        abs_path = Path(item.data(Qt.UserRole + 2))
        rel_path = item.data(Qt.UserRole)
        if is_dir:
            self.print_btn.setVisible(False)
            self.load_folder(abs_path, push_history=True)
        else:
            self.file_activated.emit(rel_path)

    def _on_print_clicked(self):
        """Émet le signal d'impression pour le fichier sélectionné."""
        item = self.list_widget.currentItem()
        if item:
            rel_path = item.data(Qt.UserRole)
            is_dir   = item.data(Qt.UserRole + 1)
            if rel_path and not is_dir:
                self.print_requested.emit(rel_path)

    # ------------------------------------------------------------------
    # Breadcrumb
    # ------------------------------------------------------------------

    def _update_breadcrumb(self):
        """Reconstruit le breadcrumb (chemin cliquable)."""
        # Vider
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if self._current_path is None:
            return

        # Calculer le chemin relatif depuis files_dir
        try:
            rel = self._current_path.relative_to(self.files_dir)
            parts = list(rel.parts)
        except ValueError:
            parts = [self._current_path.name]

        # Racine toujours présente
        all_parts = [self._t("folder_browser_root")] + parts

        for i, part in enumerate(all_parts):
            # Construire le chemin absolu pour ce segment
            if i == 0:
                segment_path = self.files_dir
            else:
                segment_path = self.files_dir / Path(*parts[:i])

            btn = QPushButton(part)
            btn.setFlat(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))

            is_last = (i == len(all_parts) - 1)
            color = self._c["text"] if is_last else self._c["breadcrumb"]
            weight = "bold" if is_last else "normal"
            btn.setStyleSheet(
                f"QPushButton {{ color: {color}; font-weight: {weight}; "
                f"  font-size: 12px; background: transparent; border: none; "
                f"  padding: 2px 4px; }}"
                f"QPushButton:hover {{ text-decoration: underline; }}"
            )
            btn.setEnabled(not is_last)

            # Capturer le chemin du segment
            _path = Path(segment_path)
            btn.clicked.connect(lambda _, p=_path: self._jump_to(p))
            self.breadcrumb_layout.addWidget(btn)

            if not is_last:
                sep = QLabel("›")
                sep.setStyleSheet(
                    f"color: {self._c['text_dim']}; font-size: 14px; padding: 0 2px;"
                )
                self.breadcrumb_layout.addWidget(sep)

        self.breadcrumb_layout.addStretch()

    def _jump_to(self, path: Path):
        """Navigation directe via le breadcrumb (empile l'historique)."""
        if path != self._current_path:
            self.load_folder(path, push_history=True)

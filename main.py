import sys
import os
import warnings

# ── Supprimer les warnings bénins des bibliothèques tierces ───────────────────
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Rediriger les erreurs MuPDF vers /dev/null (colorspace ICC non standard, etc.)
import fitz
fitz.TOOLS.mupdf_warnings()
fitz.TOOLS.reset_mupdf_warnings()

# ── Fix QtWebEngine sur Windows ───────────────────────────────────────────────
# Désactive le sandbox et le GPU qui causent des processus zombies sur
# certaines configurations Windows (crash HTML/DOCX/ODT + processus bloqués)
if sys.platform == "win32":
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
                          "--no-sandbox --disable-gpu --disable-gpu-compositing")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui     import QIcon

import config

from views.main_window import MainWindow
from database.reindex import scan_and_insert_files

def main():
    # On récupère tout depuis config.py
    db_path   = config.DB_PATH
    files_dir = config.FILES_DIR
    langs     = config.LANGUAGES_PATH

    print(f"[DEBUG] DB_PATH          : {db_path}")
    print(f"[DEBUG] FILES_DIR        : {files_dir}")
    print(f"[DEBUG] LANGUAGES_PATH   : {langs}")

    # Initialisation de la base (scan)
    scan_and_insert_files(files_dir)

    # Lancement de l'UI
    app = QApplication(sys.argv)
    favicon = config.ASSETS_DIR / "icons" / "favicon.ico"
    if favicon.exists():
        app.setWindowIcon(QIcon(str(favicon)))
    QApplication.setStyle(QStyleFactory.create("Fusion"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

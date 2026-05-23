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
# Ces variables DOIVENT être positionnées AVANT tout import Qt/PySide6.
# Sans --no-sandbox + --disable-gpu, le renderer Chromium échoue à charger
# ses DLLs sur les configs avec GPU hybride, pilotes virtuels (Parsec, Meta VR,
# USB Mobile, etc.), ce qui provoque un "DLL load failed" à l'import de
# QtWebEngineWidgets et laisse des processus zombies impossibles à tuer.
if sys.platform == "win32":
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
                          "--no-sandbox --disable-gpu --disable-gpu-compositing")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtGui     import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

import config
from views.main_window import MainWindow
from database.reindex  import scan_and_insert_files

_SERVER_NAME = "LibreGED_SingleInstance"

def _is_already_running() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)
    if socket.waitForConnected(300):
        socket.disconnectFromServer()
        return True
    return False

def _create_instance_server() -> QLocalServer:
    server = QLocalServer()
    QLocalServer.removeServer(_SERVER_NAME)
    server.listen(_SERVER_NAME)
    return server

def main():
    db_path   = config.DB_PATH
    files_dir = config.FILES_DIR
    langs     = config.LANGUAGES_PATH

    print(f"[DEBUG] DB_PATH          : {db_path}")
    print(f"[DEBUG] FILES_DIR        : {files_dir}")
    print(f"[DEBUG] LANGUAGES_PATH   : {langs}")

    scan_and_insert_files(files_dir)

    app = QApplication(sys.argv)

    if _is_already_running():
        QMessageBox.information(None, "LibreGED",
                                "LibreGED est déjà en cours d'exécution.")
        sys.exit(0)
    instance_server = _create_instance_server()

    favicon = config.ASSETS_DIR / "icons" / "favicon.ico"
    if favicon.exists():
        app.setWindowIcon(QIcon(str(favicon)))
    QApplication.setStyle(QStyleFactory.create("Fusion"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

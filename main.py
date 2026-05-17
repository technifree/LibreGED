import sys
import os

# ── Fix WebEngine Windows — forcer le rendu logiciel (SwiftShader) ────────────
# Erreur observée : SharedImageBackingFactory / native_skia_output_device /
# "Context lost during MakeCurrent" → le GPU Chromium perd son contexte OpenGL.
# Solution : désactiver totalement le GPU Chromium et basculer sur SwiftShader
# (renderer logiciel embarqué dans QtWebEngine), qui fonctionne sur toutes
# les configurations Windows sans pilote GPU compatible GLES3.
#
# Ces variables DOIVENT être définies avant toute création de QApplication.
# Désactiver le sandbox QtWebEngine (nécessaire sur Windows avec PyInstaller)
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
# Note : on n'utilise PAS --disable-gpu car v2.8.2 fonctionnait avec le GPU.
# Le crash v2.9.0 venait de la multiplication des instances QWebEngineView,
# pas du GPU. Un seul QWebEngineView est maintenant créé et réutilisé.

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtGui     import QIcon

import config

from views.main_window import MainWindow
from database.reindex import scan_and_insert_files

# ── Instance unique ───────────────────────────────────────────────────────────
# Utilise un fichier .lock (plus fiable que QLocalSocket sur Windows après crash)
import atexit
import tempfile
from pathlib import Path

_LOCK_FILE = config.USER_DATA_DIR / ".libreged.lock"

def _acquire_lock() -> bool:
    """
    Tente d'acquérir le verrou d'instance unique via un fichier PID.
    Retourne True si cette instance est la seule, False sinon.
    """
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            # Vérifier si le PID est encore vivant
            if sys.platform == "win32":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return False   # processus vivant → instance déjà ouverte
            else:
                import signal
                os.kill(pid, 0)    # lève OSError si le processus n'existe plus
                return False       # processus vivant
        except (ValueError, OSError, PermissionError):
            pass   # PID invalide ou mort → on peut continuer
    # Écrire notre propre PID
    _LOCK_FILE.write_text(str(os.getpid()))
    return True

def _release_lock():
    try:
        if _LOCK_FILE.exists():
            _LOCK_FILE.unlink()
    except Exception:
        pass

def main():
    db_path   = config.DB_PATH
    files_dir = config.FILES_DIR
    langs     = config.LANGUAGES_PATH

    print(f"[DEBUG] DB_PATH          : {db_path}")
    print(f"[DEBUG] FILES_DIR        : {files_dir}")
    print(f"[DEBUG] LANGUAGES_PATH   : {langs}")

    scan_and_insert_files(files_dir)

    app = QApplication(sys.argv)

    # ── Vérification instance unique ──────────────────────────────────────────
    if not _acquire_lock():
        QMessageBox.information(
            None, "LibreGED",
            "LibreGED est déjà en cours d'exécution."
        )
        sys.exit(0)

    # Libérer le verrou à la fermeture (normale ou crash)
    atexit.register(_release_lock)

    favicon = config.ASSETS_DIR / "icons" / "favicon.ico"
    if favicon.exists():
        app.setWindowIcon(QIcon(str(favicon)))
    QApplication.setStyle(QStyleFactory.create("Fusion"))

    window = MainWindow()
    window.show()
    result = app.exec()

    _release_lock()
    sys.exit(result)

if __name__ == "__main__":
    main()

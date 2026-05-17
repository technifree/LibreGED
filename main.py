import sys
import os

# ══════════════════════════════════════════════════════════════════════════════
# FIX GPU WINDOWS — injecter les flags Chromium via sys.argv
# ══════════════════════════════════════════════════════════════════════════════
# QTWEBENGINE_CHROMIUM_FLAGS ne fonctionne PAS avec PyInstaller car
# QtWebEngineProcess.exe est lancé AVANT que Python puisse définir des
# variables d'environnement. La seule méthode fiable : sys.argv injection,
# lue par QApplication AVANT l'initialisation du moteur WebEngine.
#
# Erreur observée : SharedImageBackingFactory / Context lost during MakeCurrent
# → GPU Chromium (Skia/ANGLE) incompatible avec le pilote Windows de l'utilisateur.
# Solution : forcer SwiftShader (renderer OpenGL LOGICIEL embarqué dans Qt).
_WEBENGINE_FLAGS = [
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--disable-gpu-rasterization",
    "--use-gl=swiftshader",
    "--disable-features=Vulkan,UseSkiaRenderer",
    "--in-process-gpu",
]
# Ajouter seulement si pas déjà présents (idempotent)
for _flag in _WEBENGINE_FLAGS:
    if _flag not in sys.argv:
        sys.argv.append(_flag)

# Sandbox également désactivé (requis PyInstaller + Windows)
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

# ══════════════════════════════════════════════════════════════════════════════

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtGui     import QIcon

import config
from views.main_window import MainWindow
from database.reindex  import scan_and_insert_files


# ── Instance unique ────────────────────────────────────────────────────────────
# Windows : Named Mutex — libéré automatiquement même en cas de crash
# Linux   : fichier PID
# ──────────────────────────────────────────────────────────────────────────────
_MUTEX_NAME = "LibreGED_SingleInstance_Mutex"
_mutex_handle = None   # maintenu en vie pendant toute l'exécution

def _acquire_lock() -> bool:
    global _mutex_handle
    if sys.platform == "win32":
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False   # une autre instance tourne
        return True        # mutex créé → on est la seule instance
    else:
        # Linux/macOS : fichier PID
        lock_file = config.USER_DATA_DIR / ".libreged.lock"
        if lock_file.exists():
            try:
                pid = int(lock_file.read_text().strip())
                os.kill(pid, 0)
                return False   # processus encore vivant
            except (ValueError, OSError):
                pass           # PID mort → continuer
        lock_file.write_text(str(os.getpid()))
        import atexit
        atexit.register(lambda: lock_file.unlink(missing_ok=True))
        return True


def main():
    print(f"[DEBUG] DB_PATH       : {config.DB_PATH}")
    print(f"[DEBUG] FILES_DIR     : {config.FILES_DIR}")
    print(f"[DEBUG] LANGUAGES     : {config.LANGUAGES_PATH}")

    scan_and_insert_files(config.FILES_DIR)

    # QApplication DOIT être créé avec sys.argv contenant les flags WebEngine
    app = QApplication(sys.argv)

    # Vérification instance unique (après QApplication pour pouvoir afficher
    # une QMessageBox)
    if not _acquire_lock():
        QMessageBox.information(
            None, "LibreGED",
            "LibreGED est déjà en cours d'exécution."
        )
        sys.exit(0)

    favicon = config.ASSETS_DIR / "icons" / "favicon.ico"
    if favicon.exists():
        app.setWindowIcon(QIcon(str(favicon)))
    QApplication.setStyle(QStyleFactory.create("Fusion"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

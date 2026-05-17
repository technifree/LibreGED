import sys
import os

# ══════════════════════════════════════════════════════════════════════════════
# FIX WINDOWS — Parsec/VirtualDisplay crash (SharedImageBackingFactory)
# Appliqué UNIQUEMENT sur Windows pour ne pas casser Linux/macOS
# ══════════════════════════════════════════════════════════════════════════════
if sys.platform == "win32":
    # Ces flags DOIVENT être définis avant tout import PySide6/Qt
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--disable-gpu "
        "--disable-gpu-compositing "
        "--use-gl=swiftshader "
        "--disable-features=Vulkan,UseSkiaRenderer"
    )

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtGui     import QIcon

import config
from views.main_window import MainWindow
from database.reindex  import scan_and_insert_files

# ── Instance unique ────────────────────────────────────────────────────────────
_MUTEX_NAME   = "LibreGED_SingleInstance_Mutex"
_mutex_handle = None

def _acquire_lock() -> bool:
    global _mutex_handle
    if sys.platform == "win32":
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
        return True
    else:
        lock_file = config.USER_DATA_DIR / ".libreged.lock"
        if lock_file.exists():
            try:
                pid = int(lock_file.read_text().strip())
                os.kill(pid, 0)
                return False
            except (ValueError, OSError):
                pass
        lock_file.write_text(str(os.getpid()))
        import atexit
        atexit.register(lambda: lock_file.unlink(missing_ok=True))
        return True


def main():
    print(f"[DEBUG] DB_PATH   : {config.DB_PATH}")
    print(f"[DEBUG] FILES_DIR : {config.FILES_DIR}")
    print(f"[DEBUG] LANGUAGES : {config.LANGUAGES_PATH}")

    scan_and_insert_files(config.FILES_DIR)

    app = QApplication(sys.argv)

    if not _acquire_lock():
        QMessageBox.information(None, "LibreGED",
                                "LibreGED est déjà en cours d'exécution.")
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

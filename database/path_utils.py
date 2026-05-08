# path_utils.py - Utilitaires pour la gestion des chemins longs sur Windows.
# Sur Windows, le prefixe \\?\ leve la limite des 259 caracteres (API NT).
# Sans effet sur Linux/macOS.

import os
import sys
from pathlib import Path



def _clean_env_for_subprocess() -> dict:
    """
    Retourne une copie de l'environnement sans LD_LIBRARY_PATH ni
    LD_PRELOAD injectés par PyInstaller. Nécessaire sous Linux pour que
    les processus externes (xdg-open, nemo, QFileDialog natif) trouvent
    leurs propres bibliothèques système au lieu de celles du bundle.
    """
    env = os.environ.copy()
    for var in ("LD_LIBRARY_PATH", "LD_PRELOAD", "GIO_MODULE_DIR",
                "GIO_EXTRA_MODULES", "GSETTINGS_SCHEMA_DIR"):
        env.pop(var, None)
    # Restaurer LD_LIBRARY_PATH système si PyInstaller l'avait sauvegardé
    orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if orig:
        env["LD_LIBRARY_PATH"] = orig
    return env


def win_path(path) -> str:
    """
    Retourne le chemin sous forme de chaîne, prêt pour les API fichiers.

    Sur Windows : ajoute le préfixe  \\?\\  si nécessaire pour lever la
    limite des 259 caractères.
    Sur Linux/macOS : retourne simplement str(path).

    À utiliser partout où un chemin est passé à :
        open(), fitz.open(), Image.open(), pd.ExcelFile(),
        os.remove(), shutil.rmtree(), ...
    """
    path_str = str(path)
    if sys.platform != "win32":
        return path_str
    # Résoudre en chemin absolu (sans résoudre les symlinks)
    path_str = os.path.abspath(path_str)
    if path_str.startswith("\\\\?\\"):
        return path_str          # déjà préfixé
    if path_str.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path_str[2:]   # chemin réseau UNC
    return "\\\\?\\" + path_str


def strip_win_prefix(path_str: str) -> str:
    """Supprime le préfixe  \\?\\  pour retrouver un chemin «normal»."""
    if path_str.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path_str[8:]
    if path_str.startswith("\\\\?\\"):
        return path_str[4:]
    return path_str


def safe_relpath(full_path, base_path) -> str | None:
    """
    Calcule le chemin relatif de *full_path* par rapport à *base_path*.
    Gère les préfixes  \\?\\  éventuels.
    Retourne None si les chemins sont sur des lecteurs différents (Windows).
    """
    clean_full = strip_win_prefix(str(full_path))
    clean_base = strip_win_prefix(str(base_path))
    try:
        return os.path.relpath(clean_full, clean_base)
    except ValueError:
        return None


def make_walk_root(base_path) -> str:
    """
    Retourne le chemin racine à passer à os.walk() pour traverser
    les dossiers avec des chemins potentiellement longs.
    """
    resolved = str(Path(base_path).resolve())
    return win_path(resolved)


def path_exists(path) -> bool:
    """os.path.exists() compatible avec les chemins longs Windows."""
    return os.path.exists(win_path(path))


def path_is_file(path) -> bool:
    """os.path.isfile() compatible avec les chemins longs Windows."""
    return os.path.isfile(win_path(path))


def path_is_dir(path) -> bool:
    """os.path.isdir() compatible avec les chemins longs Windows."""
    return os.path.isdir(win_path(path))


def path_is_symlink(path) -> bool:
    """os.path.islink() compatible avec les chemins longs Windows."""
    return os.path.islink(win_path(path))


def open_folder_in_explorer(folder_path):
    import os
    import sys
    import subprocess
    from pathlib import Path
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    path = Path(folder_path).resolve()

    # Si c'est un fichier → ouvrir son dossier
    if path.is_file():
        path = path.parent

    path_str = str(path)

    if sys.platform.startswith("win"):
        try:
            if path.exists():
                subprocess.Popen(["explorer", "/select,", os.path.abspath(path_str)])
            else:
                os.startfile(os.path.abspath(path_str))
        except Exception:
            os.startfile(os.path.abspath(path_str))

    elif sys.platform.startswith("darwin"):
        subprocess.Popen(["open", path_str])

    else:
        # Nettoyer LD_LIBRARY_PATH pour éviter les conflits de libs PyInstaller
        # avec les bibliothèques système (nemo, xdg-open, etc.)
        # Bypass QDesktopServices : Qt transmet LD_LIBRARY_PATH de PyInstaller
        # à xdg-open → nemo charge les mauvaises libs système.
        # On passe directement par subprocess avec un env propre.
        clean_env = _clean_env_for_subprocess()
        subprocess.Popen(["xdg-open", path_str], env=clean_env)
import os
import sqlite3
from pathlib import Path
from config import DB_PATH, FILES_DIR
from database.path_utils import win_path, strip_win_prefix, safe_relpath, make_walk_root


# ---------------------------------------------------------------------------
# Fonctions de base de données
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            extension TEXT,
            added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_path TEXT UNIQUE NOT NULL,
            author TEXT,
            tags TEXT,
            comment TEXT,
            version TEXT,
            updated_at TEXT,
            FOREIGN KEY(document_path) REFERENCES documents(path) ON DELETE CASCADE
        )
    """)

    conn.commit()
    return conn, cur


def insert_document(name, path, ext, cur):
    cur.execute(
        "INSERT OR IGNORE INTO documents (name, path, extension) VALUES (?, ?, ?)",
        (name, path, ext)
    )


def _safe_walk(base_path):
    """
    os.walk avec followlinks=True mais protection contre les boucles
    de symlinks circulaires via mémorisation des inodes réels.
    """
    base_path = Path(base_path)
    seen_real = set()
    try:
        root_stat = os.stat(base_path)
        seen_real.add((root_stat.st_dev, root_stat.st_ino))
    except OSError:
        return

    for root, dirs, files in os.walk(base_path, followlinks=True):
        root_path = Path(root)
        safe_dirs = []
        for d in dirs:
            dir_path = root_path / d
            try:
                real_stat = os.stat(dir_path)
                key = (real_stat.st_dev, real_stat.st_ino)
                if key not in seen_real:
                    seen_real.add(key)
                    safe_dirs.append(d)
                else:
                    print(f"[WARN] Boucle de symlink ignorée : {dir_path}")
            except OSError:
                pass
        dirs[:] = safe_dirs
        yield root, dirs, files


def scan_and_insert_files(folder_path):
    conn, cur = init_db()
    count = 0
    base_str = str(Path(folder_path).resolve())
    walk_root = make_walk_root(folder_path)

    for root, _, files in os.walk(walk_root):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = safe_relpath(full_path, base_str)
            if rel_path is None:
                continue
            ext = os.path.splitext(filename)[1].lower()
            insert_document(filename, rel_path, ext, cur)
            count += 1

    conn.commit()
    conn.close()
    print(f"[OK] {count} fichiers indexés.")


def index_files_with_progress(base_path, cur, callback=None):
    """
    Indexe tous les fichiers sous *base_path* avec un callback de progression.
    Supporte les chemins longs Windows via le préfixe \\?\.
    """
    base_str = str(Path(base_path).resolve())
    walk_root = make_walk_root(base_path)

    # 1. Collecter tous les fichiers
    all_files = []
    for root, _, files in _safe_walk(base_path):
        for file in files:
            all_files.append(os.path.join(root, file))

    total = len(all_files)
    indexed = []
    skipped = []

    # 2. Indexer avec progression
    for i, full_path in enumerate(all_files, start=1):
        rel_path = safe_relpath(full_path, base_str)

        if rel_path is None:
            skipped.append(full_path)
            if callback:
                callback(i, total)
            continue

        # Nom propre sans préfixe \\?\
        name = os.path.basename(strip_win_prefix(full_path))
        ext  = os.path.splitext(name)[1].lower()

        cur.execute("""
            INSERT OR IGNORE INTO documents (name, path, extension)
            VALUES (?, ?, ?)
        """, (name, rel_path, ext))

        indexed.append(rel_path)

        if callback:
            callback(i, total)

    if skipped:
        print(f"[AVERTISSEMENT] {len(skipped)} fichier(s) ignoré(s) "
              f"(chemin relatif non calculable) :")
        for p in skipped[:10]:
            print(f"  - {strip_win_prefix(p)}")
        if len(skipped) > 10:
            print(f"  ... et {len(skipped) - 10} autre(s).")

    return indexed


def index_files(base_path, cur):
    base_str = str(Path(base_path).resolve())
    walk_root = make_walk_root(base_path)
    indexed = []

    for root, _, files in _safe_walk(base_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = safe_relpath(full_path, base_str)
            if rel_path is None:
                continue
            name = os.path.basename(strip_win_prefix(full_path))
            ext  = os.path.splitext(name)[1].lower()
            cur.execute("""
                INSERT OR IGNORE INTO documents (name, path, extension)
                VALUES (?, ?, ?)
            """, (name, rel_path, ext))
            indexed.append(rel_path)

    return indexed


def clean_removed(indexed, cur):
    cur.execute("SELECT path FROM documents")
    known_paths = {row[0] for row in cur.fetchall()}
    removed = known_paths - set(indexed)

    for path in removed:
        cur.execute("DELETE FROM documents WHERE path = ?", (path,))

    cur.execute("""
        DELETE FROM document_metadata
        WHERE document_path NOT IN (SELECT path FROM documents)
    """)

    return removed


def reindex_files_with_progress(callback=None):
    conn, cur = init_db()
    indexed = index_files_with_progress(FILES_DIR, cur, callback)
    clean_removed(indexed, cur)

    # Purge des symlinks brisés
    base_str  = str(Path(FILES_DIR).resolve())
    walk_root = make_walk_root(FILES_DIR)

    for root, dirs, files in os.walk(walk_root, followlinks=False):
        for name in dirs + files:
            full = os.path.join(root, name)
            clean = strip_win_prefix(full)
            try:
                is_link      = os.path.islink(clean)
                target_alive = os.path.exists(clean)
            except (OSError, ValueError):
                continue

            if is_link and not target_alive:
                rel = safe_relpath(clean, base_str)
                if rel:
                    rel_posix = rel.replace(os.sep, "/")
                    try:
                        os.unlink(clean)
                    except OSError:
                        pass
                    for r in (rel, rel_posix):
                        cur.execute("DELETE FROM documents WHERE path = ?", (r,))
                        cur.execute("DELETE FROM document_metadata WHERE document_path = ?", (r,))

    conn.commit()
    conn.close()
    return len(indexed)

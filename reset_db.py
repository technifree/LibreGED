from pathlib import Path
import sqlite3
import os

DB_PATH = Path(__file__).resolve().parent / "database" / "db.db"
FILES_DIR = Path(__file__).resolve().parent / "files"

def reset_database():
    if not DB_PATH.exists():
        print(f"Base de données introuvable : {DB_PATH}")
        return

    print("Connexion à la base...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Réinitialiser la table documents
    print("Suppression des anciennes données...")
    cursor.execute("DELETE FROM documents")

    print("Réindexation des fichiers présents dans :", FILES_DIR)

    for root, dirs, files in os.walk(FILES_DIR):
        for name in files:
            relative_path = os.path.relpath(os.path.join(root, name), FILES_DIR)
            full_name = name
            print(f"Insertion : {full_name} → {relative_path}")
            cursor.execute("INSERT INTO documents (name, path) VALUES (?, ?)", (full_name, relative_path))

    conn.commit()
    conn.close()
    print("✅ Base de données réinitialisée avec succès.")

if __name__ == "__main__":
    reset_database()

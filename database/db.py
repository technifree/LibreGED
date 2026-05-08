import os
import sqlite3
from config import DB_PATH, FILES_DIR  # Importer depuis config
from . import odf_utils
from pathlib import Path

def fetch_all_documents():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, path, extension FROM documents")
        return cur.fetchall()

def matches_content(file_path, query, translate):
    ext = os.path.splitext(file_path)[1].lower()
    query = query.lower()

    try:
        if ext in [".txt", ".md", ".html", ".htm", ".py"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return query in f.read().lower()

        elif ext == ".pdf":
            import fitz
            with fitz.open(file_path) as doc_pdf:
                for page in doc_pdf:
                    if query in page.get_text().lower():
                        return True

        elif ext in [".doc", ".docx"]:
            try:
                import mammoth
                with open(file_path, "rb") as docx_file:
                    result = mammoth.convert_to_html(docx_file)
                    return query in result.value.lower()
            except:
                from docx import Document
                doc = Document(file_path)
                return any(query in p.text.lower() for p in doc.paragraphs)

        elif ext == ".epub":
            from ebooklib import epub
            from bs4 import BeautifulSoup
            book = epub.read_epub(str(file_path))
            for item in book.get_items():
                if item.get_type() == 9:  # 9 = DOCUMENT
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    if query in soup.get_text().lower():
                        return True

        elif ext in [".odt", ".odf"]:
            content = odf_utils.extract_text_from_odt(file_path)
            return query in content.lower()

        elif ext == ".ods":
            content = odf_utils.ods_to_html(file_path)
            return query in content.lower()

        elif ext == ".odp":
            content = odf_utils.odp_to_html(file_path)
            return query in content.lower()
        
        elif ext == ".xlsx":
            content = odf_utils.extract_text_from_xlsx(file_path)
            if content:
                return query in content.lower()
            
        elif ext == ".pptx":
            content = odf_utils.extract_text_from_pptx(file_path)
            if content:
                return query in content.lower()


    except Exception as e:
        print(f"[WARN] {translate('file_read_error')} '{file_path}': {e}")

    return False

def search_documents(keywords_string, translate):
    results = []

    # 1. Découpe et nettoyage des mots-clés
    # Supporte virgules, espaces, ou combinaison des deux
    import re
    keywords = [kw.strip().lower() for kw in re.split(r"[,\s]+", keywords_string) if kw.strip()]

    if not keywords:
        return []

    for doc in fetch_all_documents():
        name, path, ext = doc[1], doc[2], doc[3]
        full_path = FILES_DIR / path
        all_keywords_found = True

        for kw in keywords:
            kw_found = False

            # Recherche dans le nom ou le chemin
            if kw in name.lower() or kw in path.lower():
                kw_found = True

            # Sinon, recherche dans le contenu du fichier
            elif matches_content(str(full_path), kw, translate):
                kw_found = True

            if not kw_found:
                all_keywords_found = False
                break  # Ce mot-clé n’est pas dans ce fichier → on sort

        if all_keywords_found:
            results.append(doc)

    return results


def save_metadata_to_db(document_path, metadata):
    print(f"[DB] Enregistrement metadata pour {document_path} : {metadata}")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            # Vérification : ce document existe-t-il ?
            cur.execute("SELECT 1 FROM documents WHERE path = ?", (document_path,))
            if not cur.fetchone():
                print(f"[ERREUR] Aucun document avec path = '{document_path}' dans la table 'documents'")
                return

            cur.execute("""
                INSERT INTO document_metadata (document_path, author, tags, comment, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_path) DO UPDATE SET
                    author = excluded.author,
                    tags = excluded.tags,
                    comment = excluded.comment,
                    version = excluded.version,
                    updated_at = excluded.updated_at
            """, (
                document_path,
                metadata.get("author"),
                metadata.get("tags"),
                metadata.get("comment"),
                metadata.get("version"),
                metadata.get("updated_at")
            ))
            conn.commit()
            cur.execute("SELECT * FROM document_metadata")
            rows = cur.fetchall()
            print(f"[DEBUG] document_metadata contient : {rows}")

            print("[DB] Commit terminé.")

    except Exception as e:
        print(f"[ERREUR SQLITE] {e}")

def get_metadata_for_path(path):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT author, tags, comment, version, updated_at
            FROM document_metadata
            WHERE document_path = ?
        """, (path,))
        row = cur.fetchone()
        if row:
            return {
                "author": row[0] or "",
                "tags": row[1] or "",
                "comment": row[2] or "",
                "version": row[3] or "",
                "updated_at": row[4] or ""
            }
        return None

def get_all_tags():
    import sqlite3
    from config import DB_PATH  # si ce n’est pas déjà importé

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tags FROM document_metadata")
    rows = cur.fetchall()
    conn.close()

    tag_set = set()
    for row in rows:
        if row and row[0]:
            tag_set.update(t.strip() for t in row[0].split(",") if t.strip())

    return list(tag_set)


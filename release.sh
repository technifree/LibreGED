#!/bin/bash
# release.sh — Compile, package et publie une release LibreGED (Linux + Windows + macOS)
# Usage : ./release.sh vX.Y.Z "Description courte des changements"

set -e

VERSION="${1}"
NOTES="${2:-Nouvelle version}"
SKIP_MACOS="${SKIP_MACOS:-0}"

# ── Vérifications ─────────────────────────────────────────────────────────────
if [ -z "$VERSION" ]; then
    echo "Usage : ./release.sh vX.Y.Z \"Description\""
    echo "Exemple : ./release.sh v2.8.1 \"Fix crash renommage, Ctrl+F\""
    exit 1
fi

for cmd in gh docker; do
    if ! command -v $cmd &>/dev/null; then
        echo "[ERREUR] $cmd non installé"
        exit 1
    fi
done

if ! gh auth status &>/dev/null; then
    echo "[ERREUR] GitHub CLI non authentifié → gh auth login"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  Release LibreGED $VERSION"
echo "══════════════════════════════════════════════════"
echo ""

# ── Étape 1 : Commit + push EN PREMIER ────────────────────────────────────────
# IMPORTANT : pousser avant les builds GitHub Actions,
# sinon les runners compilent l'ancienne version du code.
echo "[1/6] Commit et push du code source..."
git add .
git commit -m "$VERSION — $NOTES" 2>/dev/null || echo "      (rien à committer)"
git pull --rebase origin master --quiet
git push --quiet
echo "      OK — code source à jour sur GitHub"

# ── Étape 2 : Build Linux ──────────────────────────────────────────────────────
echo "[2/6] Build Linux (Docker Ubuntu 22.04)..."
./build_linux.sh
echo "      OK"

# ── Étape 3 : Build Windows ───────────────────────────────────────────────────
echo "[3/6] Build Windows (GitHub Actions)..."
./build_windows.sh master
echo "      OK"

# ── Étape 4 : Build macOS ─────────────────────────────────────────────────────
if [ "$SKIP_MACOS" = "1" ]; then
    echo "[4/6] Build macOS ignoré (SKIP_MACOS=1)"
else
    echo "[4/6] Build macOS (GitHub Actions)..."
    ./build_macos.sh master
    echo "      OK"
fi

# ── Étape 5 : Archives ────────────────────────────────────────────────────────
echo "[5/6] Création des archives..."
rm -f LibreGED-linux.tar.gz
cd dist && tar -czf ../LibreGED-linux.tar.gz LibreGED/ && cd ..
echo "      Linux  : LibreGED-linux.tar.gz  ($(du -sh LibreGED-linux.tar.gz | cut -f1))"
echo "      Windows: LibreGED-windows.zip   ($(du -sh LibreGED-windows.zip | cut -f1))"
[ -f LibreGED-macos.zip ] && echo "      macOS  : LibreGED-macos.zip    ($(du -sh LibreGED-macos.zip | cut -f1))"

# ── Étape 6 : Release GitHub ──────────────────────────────────────────────────
echo "[6/6] Publication de la release GitHub $VERSION..."

ASSETS="LibreGED-linux.tar.gz LibreGED-windows.zip"
[ -f LibreGED-macos.zip ] && ASSETS="$ASSETS LibreGED-macos.zip"

gh release create "$VERSION" \
    $ASSETS \
    --title "LibreGED $VERSION" \
    --notes "$NOTES"

echo ""
echo "══════════════════════════════════════════════════"
echo "  Terminé !"
echo "  https://github.com/technifree/LibreGED/releases/tag/$VERSION"
echo "══════════════════════════════════════════════════"
echo ""

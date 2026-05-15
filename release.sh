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
    echo "Exemple : ./release.sh v2.8.2 \"Fix crash Windows, EML, MHTML\""
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

# ── Étape 1 : Mise à jour du README ───────────────────────────────────────────
echo "[1/7] Mise à jour du README..."
TODAY=$(date +'%d %B %Y' | LC_ALL=fr_FR.UTF-8 date -f - +'%d %B %Y' 2>/dev/null || date +'%d/%m/%Y')
VERSION_NUM="${VERSION#v}"   # retire le "v" → 2.8.2

# Remplacer le badge de version (tous les formats possibles)
sed -i "s/version-[0-9]\+\.[0-9]\+\.[0-9]\+/version-${VERSION_NUM}/g" README.md

# Remplacer la date (format "DD mois YYYY" ou "DD/MM/YYYY")
sed -i "s/Mise à jour :.*$/Mise à jour : $(date +'%d %B %Y')/" README.md

git add README.md
echo "      OK — README mis à jour (v${VERSION_NUM}, $(date +'%d %B %Y'))"

# ── Étape 2 : Commit + push EN PREMIER ────────────────────────────────────────
echo "[2/7] Commit et push du code source..."
git add .
git commit -m "$VERSION — $NOTES" 2>/dev/null || echo "      (rien à committer)"
git pull --rebase origin master --quiet
git push --quiet
echo "      OK — code source à jour sur GitHub"

# ── Étape 3 : Build Linux ──────────────────────────────────────────────────────
echo "[3/7] Build Linux (Docker Ubuntu 22.04)..."
./build_linux.sh
echo "      OK"

# ── Étape 4 : Build Windows ───────────────────────────────────────────────────
echo "[4/7] Build Windows (GitHub Actions)..."
./build_windows.sh master
echo "      OK"

# ── Étape 5 : Build macOS ─────────────────────────────────────────────────────
if [ "$SKIP_MACOS" = "1" ]; then
    echo "[5/7] Build macOS ignoré (SKIP_MACOS=1)"
else
    echo "[5/7] Build macOS (GitHub Actions)..."
    ./build_macos.sh master
    echo "      OK"
fi

# ── Étape 6 : Archives ────────────────────────────────────────────────────────
echo "[6/7] Création des archives..."
rm -f LibreGED-linux.tar.gz
cd dist && tar -czf ../LibreGED-linux.tar.gz LibreGED/ && cd ..
echo "      Linux  : LibreGED-linux.tar.gz  ($(du -sh LibreGED-linux.tar.gz | cut -f1))"
echo "      Windows: LibreGED-windows.zip   ($(du -sh LibreGED-windows.zip | cut -f1))"
[ -f LibreGED-macos.zip ] && echo "      macOS  : LibreGED-macos.zip    ($(du -sh LibreGED-macos.zip | cut -f1))"

# ── Étape 7 : Release GitHub ──────────────────────────────────────────────────
echo "[7/7] Publication de la release GitHub $VERSION..."

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

#!/bin/bash
# update_readme.sh — Met à jour uniquement la présentation GitHub (README.md)
# Sans toucher aux releases existantes ni déclencher de build.
# Usage : ./update_readme.sh

set -e

# ── Vérifications ─────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "[ERREUR] git non installé"
    exit 1
fi

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "[ERREUR] Ce répertoire n'est pas un dépôt git"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  Mise à jour de la présentation GitHub (README)"
echo "══════════════════════════════════════════════════"
echo ""

# ── Mettre à jour les dates dans le README ────────────────────────────────────
DATE_EN=$(LC_ALL=en_US.UTF-8 date +'%-d %B %Y' 2>/dev/null || date +'%d/%m/%Y')
DATE_FR=$(LC_ALL=fr_FR.UTF-8 date +'%-d %B %Y' 2>/dev/null || date +'%d/%m/%Y')

sed -i "s|\*Last updated:.*\*|\*Last updated: ${DATE_EN}\*|g" README.md
sed -i "s|\*Mise à jour :.*\*|\*Mise à jour : ${DATE_FR}\*|g" README.md

echo "  Dates : EN → ${DATE_EN} / FR → ${DATE_FR}"

# ── Commiter si des changements existent ──────────────────────────────────────
if git diff --quiet README.md; then
    echo "  README.md inchangé — pas de nouveau commit"
else
    git add README.md
    git commit -m "docs: mise à jour de la présentation GitHub"
    echo "  ✅ Commit créé"
fi

# ── Toujours pousser (commits en attente éventuels) ───────────────────────────
PENDING=$(git log origin/master..HEAD --oneline 2>/dev/null | wc -l)
if [ "$PENDING" -gt 0 ]; then
    echo "  $PENDING commit(s) en attente → push..."
    git stash --quiet 2>/dev/null || true
    git pull --rebase origin master --quiet
    git stash pop --quiet 2>/dev/null || true
    git push --quiet
    echo "  ✅ Poussé sur GitHub"
else
    echo "  Rien à pousser (déjà à jour)"
fi

echo ""
echo "  https://github.com/technifree/LibreGED#readme"
echo ""

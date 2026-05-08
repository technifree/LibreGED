#!/bin/bash
# build_windows.sh — Compile LibreGED pour Windows via GitHub Actions
# Prérequis : gh (GitHub CLI) installé et authentifié → sudo apt install gh && gh auth login

set -e

# ── Configuration ─────────────────────────────────────────────
WORKFLOW="build_windows.yml"
ARTIFACT="LibreGED-windows"
BRANCH="${1:-main}"          # branche cible (défaut : main)
POLL_INTERVAL=20             # secondes entre chaque vérification
# ──────────────────────────────────────────────────────────────

# Vérifications préalables
if ! command -v gh &>/dev/null; then
    echo "[ERREUR] GitHub CLI (gh) non installé."
    echo "  → sudo apt install gh"
    echo "  → gh auth login"
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "[ERREUR] GitHub CLI non authentifié. Lance : gh auth login"
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo "[ERREUR] Impossible de détecter le dépôt GitHub."
    echo "         Assure-toi d'être dans un dépôt git lié à GitHub."
    exit 1
fi

echo "══════════════════════════════════════════════"
echo " Build Windows — LibreGED"
echo " Dépôt  : $REPO"
echo " Branche: $BRANCH"
echo "══════════════════════════════════════════════"
echo ""

# Déclencher le workflow
echo "[1/3] Déclenchement du workflow $WORKFLOW..."
gh workflow run "$WORKFLOW" --ref "$BRANCH"
sleep 5  # laisser GitHub enregistrer le run

# Récupérer l'ID du run le plus récent
RUN_ID=$(gh run list --workflow="$WORKFLOW" --limit=1 --json databaseId -q '.[0].databaseId')
echo "      Run ID : $RUN_ID"
echo "      Suivi  : https://github.com/$REPO/actions/runs/$RUN_ID"
echo ""

# Attendre la fin du run
echo "[2/3] Compilation en cours..."
while true; do
    STATUS=$(gh run view "$RUN_ID" --json status,conclusion -q '[.status, .conclusion] | join("|")')
    STATE="${STATUS%%|*}"
    CONCLUSION="${STATUS##*|}"

    if [ "$STATE" = "completed" ]; then
        echo ""
        if [ "$CONCLUSION" = "success" ]; then
            echo "      ✓ Build réussi !"
        else
            echo "      ✗ Build échoué (conclusion: $CONCLUSION)"
            echo "        Détails : https://github.com/$REPO/actions/runs/$RUN_ID"
            exit 1
        fi
        break
    fi

    printf "."
    sleep "$POLL_INTERVAL"
done

# Télécharger l'artifact
echo ""
echo "[3/3] Téléchargement de l'artifact..."
rm -rf "$ARTIFACT" "${ARTIFACT}.zip"
gh run download "$RUN_ID" --name "$ARTIFACT" --dir "$ARTIFACT"

# Repack en zip propre si le dossier contient le zip
if [ -f "$ARTIFACT/LibreGED-windows.zip" ]; then
    mv "$ARTIFACT/LibreGED-windows.zip" .
    rm -rf "$ARTIFACT"
    echo ""
    echo "══════════════════════════════════════════════"
    echo " Terminé → LibreGED-windows.zip"
    echo "══════════════════════════════════════════════"
else
    echo ""
    echo "══════════════════════════════════════════════"
    echo " Terminé → dossier $ARTIFACT/"
    echo "══════════════════════════════════════════════"
fi

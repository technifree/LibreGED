#!/bin/bash
# build_macos.sh — Compile LibreGED pour macOS via GitHub Actions
# Prérequis : gh (GitHub CLI) installé et authentifié

set -e

WORKFLOW="build_macos.yml"
ARTIFACT="LibreGED-macos"
BRANCH="${1:-master}"
POLL_INTERVAL=20

if ! command -v gh &>/dev/null; then
    echo "[ERREUR] GitHub CLI non installé → sudo apt install gh"
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "[ERREUR] GitHub CLI non authentifié → gh auth login"
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo "[ERREUR] Impossible de détecter le dépôt GitHub."
    exit 1
fi

echo "══════════════════════════════════════════════"
echo " Build macOS — LibreGED"
echo " Dépôt  : $REPO"
echo " Branche: $BRANCH"
echo "══════════════════════════════════════════════"
echo ""

echo "[1/3] Déclenchement du workflow $WORKFLOW..."
gh workflow run "$WORKFLOW" --ref "$BRANCH"
sleep 5

RUN_ID=$(gh run list --workflow="$WORKFLOW" --limit=1 --json databaseId -q '.[0].databaseId')
echo "      Run ID : $RUN_ID"
echo "      Suivi  : https://github.com/$REPO/actions/runs/$RUN_ID"
echo ""

echo "[2/3] Compilation en cours..."
while true; do
    STATUS=$(gh run view "$RUN_ID" --json status,conclusion -q '[.status, .conclusion] | join("|")')
    STATE="${STATUS%%|*}"
    CONCLUSION="${STATUS##*|}"

    if [ "$STATE" = "completed" ]; then
        echo ""
        if [ "$CONCLUSION" = "success" ]; then
            echo "      OK"
        else
            echo "      ECHEC (conclusion: $CONCLUSION)"
            echo "      Détails : https://github.com/$REPO/actions/runs/$RUN_ID"
            exit 1
        fi
        break
    fi
    printf "."
    sleep "$POLL_INTERVAL"
done

echo ""
echo "[3/3] Téléchargement de l'artifact..."
rm -rf "$ARTIFACT" "${ARTIFACT}.zip"
gh run download "$RUN_ID" --name "$ARTIFACT" --dir "$ARTIFACT"

if [ -f "$ARTIFACT/LibreGED-macos.zip" ]; then
    mv "$ARTIFACT/LibreGED-macos.zip" .
    rm -rf "$ARTIFACT"
    echo ""
    echo "══════════════════════════════════════════════"
    echo " Terminé → LibreGED-macos.zip"
    echo "══════════════════════════════════════════════"
else
    echo ""
    echo "══════════════════════════════════════════════"
    echo " Terminé → dossier $ARTIFACT/"
    echo "══════════════════════════════════════════════"
fi

<div align="center">

<img src="assets/icons/favicon.ico" width="80" alt="LibreGED"/>

# LibreGED

**Gestionnaire de documents personnel — simple, portable et puissant**

[![Version](https://img.shields.io/badge/version-2.9.1-blue?style=flat-square)](https://github.com/technifree/LibreGED/releases)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey?style=flat-square)](https://github.com/technifree/LibreGED/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=flat-square&logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.9-green?style=flat-square)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)](LICENSE)
[![Website](https://img.shields.io/badge/website-technifree.com-blueviolet?style=flat-square)](https://technifree.com)

*Mise à jour : 18 mai 2026

[Site web](https://technifree.com) &nbsp;·&nbsp; [Télécharger](https://github.com/technifree/LibreGED/releases) &nbsp;·&nbsp; [Signaler un bug](https://github.com/technifree/LibreGED/issues)

</div>

---

## Présentation

**LibreGED** est une solution simple et légère de **Gestion Électronique de Documents** (GED), conçue pour les utilisateurs souhaitant organiser, prévisualiser et gérer leurs documents personnels sans complexité.

Développée avec **Python** et **PySide6**, LibreGED est une application **portable**, **sécurisée** et **multiplateforme**, compatible avec une large variété de formats de fichiers.

---

## Fonctionnalités

### Navigation & Organisation

- Arborescence de fichiers intuitive et réactive
- Navigation visuelle style Nautilus avec aperçus en vignettes
- Formats supportés : **PDF, DOCX, XLSX, ODT, PPTX, HTML, MD, TXT, images...**
- Ajout de fichiers par **copie** ou **lien symbolique** vers n'importe quel emplacement du disque
- Accès rapide au dossier contenant le fichier sélectionné (clic droit)

### Prévisualisation intégrée

- Visualisation instantanée sans ouvrir d'application tierce
- PDF avec navigation page par page et zoom
- Prévisualisation de Word, Excel, PowerPoint, images, HTML, Markdown
- Zoom sur les images

### Métadonnées & Recherche

- Association de **métadonnées** à chaque document : auteur, version, date, tags, commentaires
- **Recherche avancée** dans les noms, les contenus et les tags
- Base de données SQLite locale pour un accès rapide

### Sauvegarde

- Sauvegarde manuelle de la GED dans une **archive compressée datée**

---

## Interface

LibreGED propose **12 thèmes** sélectionnables depuis l'application :

| Thèmes clairs | Thèmes sombres |
|---|---|
| Clair, Arctique, Sépia | Sombre, Café, Crépuscule |
| | Océan, Forêt, Coucher de soleil |
| | Rose, Ardoise, Minuit |

L'interface est entièrement **responsive** et s'adapte à toutes les tailles d'écran.

---

## Langues supportées

Français, Anglais, Allemand, Italien, Espagnol, Néerlandais, Portugais, Polonais, Suédois, Danois, Finnois, Grec, Tchèque.

---

## Compatibilité

| Système | Support |
|---|:---:|
| Linux (Ubuntu 22.04+, Mint, Debian, LMDE...) | Oui |
| Windows 10 / 11 | Oui |
| Distribution portable (sans installation) | Oui |

---

## Installation

Rendez-vous sur la page [**Releases**](https://github.com/technifree/LibreGED/releases) et téléchargez l'archive correspondant à votre système.

**Linux**
```bash
tar -xzf LibreGED-linux.tar.gz
cd LibreGED
./LibreGED
```

**Windows**
```
Décompresser LibreGED-windows.zip
Double-cliquer sur LibreGED.exe
```

> Aucune installation requise. LibreGED est entièrement portable.

---

## Compilation depuis les sources

Prérequis : Python 3.10+, pip

```bash
git clone https://github.com/technifree/LibreGED.git
cd LibreGED
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Build Linux (via Docker) :
```bash
./build_linux.sh
```

Build Windows (via GitHub Actions) :
```bash
./build_windows.sh master
```

---

## Sécurité & Performance

- Accès aux fichiers limité au répertoire GED configuré
- Données stockées localement dans une base SQLite
- Aucune donnée transmise vers l'extérieur
- Optimisé pour les grands volumes de documents

---

## Licence

LibreGED est distribué sous licence **MIT**.  
Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

<div align="center">

Développé par [technifree](https://technifree.com)

</div>

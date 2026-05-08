#!/bin/bash

docker run --rm \
  -v "$(pwd)":/app \
  -w /app \
  -e HOST_UID=$(id -u) \
  -e HOST_GID=$(id -g) \
  ubuntu:22.04 \
  bash -c "
    export DEBIAN_FRONTEND=noninteractive &&
    apt-get update -q &&
    apt-get install -y python3 python3-venv python3-pip python3-dev \
      libgl1 libglib2.0-0 libdbus-1-3 \
      libheif-dev libde265-dev &&
    python3 -m venv /tmp/venv &&
    /tmp/venv/bin/pip install --upgrade pip &&
    /tmp/venv/bin/pip install -r requirements.txt &&
    /tmp/venv/bin/pip uninstall -y pathlib 2>/dev/null || true &&
    /tmp/venv/bin/pyinstaller \
      --noconfirm \
      --onedir \
      --windowed \
      --icon=assets/icons/favicon.ico \
      --name=LibreGED \
      --distpath=dist \
      --add-data 'assets:assets' \
      --add-data 'files:files' \
      --add-data 'config.py:.' \
      --add-data 'styles.py:.' \
      --hidden-import=views \
      --hidden-import=views.main_window \
      --hidden-import=views.folder_browser \
      --hidden-import=database \
      --hidden-import=database.db \
      --hidden-import=database.reindex \
      --hidden-import=database.odf_utils \
      --hidden-import=database.path_utils \
      --hidden-import=pymupdf \
      --hidden-import=fitz \
      --hidden-import=numpy \
      --hidden-import=matplotlib \
      --hidden-import=pandas \
      --hidden-import=reportlab \
      --hidden-import=ebooklib \
      --hidden-import=bs4 \
      --hidden-import=odf \
      --hidden-import=docx \
      --hidden-import=openpyxl \
      --hidden-import=lxml \
      --hidden-import=pptx \
      --hidden-import=mammoth \
      --hidden-import=humanize \
      --hidden-import=qtawesome \
      --hidden-import=PIL \
      --hidden-import=PIL.Image \
      --hidden-import=PIL.ImageQt \
      --hidden-import=PySide6.QtWebEngineWidgets \
      --hidden-import=PySide6.QtWebEngineCore \
      --hidden-import=PySide6.QtWebEngine \
      --hidden-import=PySide6.QtPrintSupport \
      --collect-all=qtawesome \
      --collect-all=pymupdf \
      --collect-all=fitz \
      main.py &&
    echo '[POST-BUILD] Suppression des libs système conflictuelles...' &&
    for lib in \
      libstdc++.so.6     libgcc_s.so.1      \
      libglib-2.0.so.0   libgobject-2.0.so.0 libgio-2.0.so.0 \
      libgmodule-2.0.so.0 libgthread-2.0.so.0 \
      libmount.so.1      libblkid.so.1      libuuid.so.1 \
      libz.so.1          libdbus-1.so.3     \
      libselinux.so.1    libpcre2-8.so.0    libffi.so.8 \
      liblzma.so.5       libzstd.so.1       libbz2.so.1 \
      libudev.so.1       libsystemd.so.0    \
    ; do
      rm -fv dist/LibreGED/_internal/\${lib}*
    done &&
    echo '[POST-BUILD] OK' &&
    chown -R \$HOST_UID:\$HOST_GID dist/
  "

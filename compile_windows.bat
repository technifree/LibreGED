@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist LibreGED.spec del /q LibreGED.spec

py -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --icon=assets\icons\favicon.ico ^
  --name=LibreGED ^
  --distpath=dist ^
  --add-data "assets;assets" ^
  --add-data "files;files" ^
  --add-data "config.py;." ^
  --add-data "styles.py;." ^
  --hidden-import=views ^
  --hidden-import=views.main_window ^
  --hidden-import=views.folder_browser ^
  --hidden-import=database ^
  --hidden-import=database.db ^
  --hidden-import=database.reindex ^
  --hidden-import=database.odf_utils ^
  --hidden-import=database.path_utils ^
  --hidden-import=pymupdf ^
  --hidden-import=fitz ^
  --hidden-import=numpy ^
  --hidden-import=matplotlib ^
  --hidden-import=pandas ^
  --hidden-import=reportlab ^
  --hidden-import=ebooklib ^
  --hidden-import=bs4 ^
  --hidden-import=odf ^
  --hidden-import=docx ^
  --hidden-import=openpyxl ^
  --hidden-import=lxml ^
  --hidden-import=pptx ^
  --hidden-import=mammoth ^
  --hidden-import=humanize ^
  --hidden-import=qtawesome ^
  --hidden-import=PIL ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageQt ^
  --hidden-import=PySide6.QtWebEngineWidgets ^
  --hidden-import=PySide6.QtWebEngineCore ^
  --hidden-import=PySide6.QtWebEngine ^
  --hidden-import=PySide6.QtPrintSupport ^
  --collect-all=qtawesome ^
  --collect-all=pymupdf ^
  --collect-all=fitz ^
  main.py

if errorlevel 1 (
    echo.
    echo Echec de la compilation.
    endlocal
    pause
    exit /b 1
)

echo.
echo Compilation terminee.
endlocal
pause
exit /b 0

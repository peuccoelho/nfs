@echo off
title Compilando Rei das NFS...

echo ============================================
echo  Rei das NFS - Build Script
echo ============================================
echo.

REM Verifica se pyinstaller esta instalado
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [INSTALANDO] PyInstaller...
    pip install pyinstaller
)

echo [LIMPEZA] Removendo builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

echo.
echo [COMPILANDO] Gerando executavel...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Rei_das_NFS" ^
    --icon "img\icone.ico" ^
    --add-data ".env.example;." ^
    --add-data "requirements.txt;." ^
    --hidden-import "playwright.async_api" ^
    --hidden-import "playwright.sync_api" ^
    --hidden-import "dotenv" ^
    --hidden-import "calendar" ^
    --hidden-import "zipfile" ^
    --hidden-import "tempfile" ^
    --hidden-import "shutil" ^
    --hidden-import "re" ^
    --exclude-module "tkinter.test" ^
    --exclude-module "unittest" ^
    --exclude-module "pdb" ^
    --exclude-module "test" ^
    --noconfirm ^
    gui.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Compilacao falhou!
    pause
    exit /b 1
)

echo.
echo [SUCESSO] Compilacao concluida!
echo.
echo Executavel gerado em:
echo   %cd%\dist\Rei das NFS.exe
echo.
echo Tamanho:
for %%I in ("dist\Rei das NFS.exe") do echo   %%~zI bytes
echo.
echo Para instalar o Playwright (necessario na primeira execucao):
echo   "dist\Rei das NFS.exe" --install-playwright
echo.
pause

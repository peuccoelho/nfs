@echo off
title Compilando Omie NFSe Automation...

echo ============================================
echo  Omie NFSe Automation - Build Script
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
if exist "Omie_NFSe_Automation.spec" del /q "Omie_NFSe_Automation.spec"

echo.
echo [COMPILANDO] Gerando executavel...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Omie_NFSe_Automation" ^
    --icon "img\icone.ico" ^
    --add-data ".env.example;." ^
    --add-data "requirements.txt;." ^
    --collect-all "omie" ^
    --hidden-import "playwright.async_api" ^
    --hidden-import "playwright.sync_api" ^
    --hidden-import "dotenv" ^
    --hidden-import "tkinter" ^
    --exclude-module "tkinter.test" ^
    --exclude-module "unittest" ^
    --exclude-module "pdb" ^
    --exclude-module "test" ^
    --noconfirm ^
    gui_omie.py

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
echo   %cd%\dist\Omie_NFSe_Automation.exe
echo.
pause

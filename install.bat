@echo off
REM ============================================================
REM  Antigravity Obsidian Brain — Instalacao (Windows)
REM ============================================================

echo.
echo   Brain Antigravity Obsidian Brain — Instalador
echo   ============================================
echo.

REM 1. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   X Python nao encontrado. Instale: https://python.org
    pause
    exit /b 1
)

echo   OK Python encontrado

REM 2. Criar virtualenv
if not exist "venv" (
    echo   Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo   OK Ambiente virtual ativado

REM 3. Instalar dependencias
echo   Instalando dependencias...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

REM 4. Copiar config se nao existir
if not exist "config.yaml" (
    copy config.example.yaml config.yaml >nul
    echo   OK config.yaml criado
)

echo.
echo   OK Instalacao concluida!
echo.
echo   Proximos passos:
echo     1. Edite config.yaml com o caminho do seu vault
echo     2. Execute: venv\Scripts\activate.bat
echo     3. Execute: python -m brain sync
echo     4. Abra o Obsidian e aponte para o vault criado
echo.
pause

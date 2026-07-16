@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Nexus Server — FastAPI
echo ========================================
echo.

if not exist ".env" (
  if exist ".env.example" (
    echo Creating .env from .env.example ...
    copy /Y ".env.example" ".env" >nul
    echo Edit Server\.env and set PG_CONNECTION before chatting.
    echo.
  ) else (
    echo ERROR: .env.example not found.
    pause
    exit /b 1
  )
)

set "PYTHONPATH=%CD%"
set "HAS_UV=0"
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 set "HAS_UV=1"

REM ── 1. Ensure .venv exists ────────────────────────────────────────────────
echo Setting up virtual environment ^(.venv^) ...
if exist ".venv\Scripts\python.exe" (
  echo .venv already present.
) else (
  if "%HAS_UV%"=="1" (
    echo Creating .venv with uv ^(Python 3.13^) ...
    if exist ".python-version" (
      uv venv --python 3.13
    ) else (
      uv venv
    )
  ) else (
    where python >nul 2>&1
    if errorlevel 1 (
      echo ERROR: Neither "uv" nor "python" found on PATH.
      echo Install uv ^(https://github.com/astral-sh/uv^) or Python 3.13+.
      pause
      exit /b 1
    )
    echo Creating .venv with python -m venv ...
    python -m venv .venv
  )
  if errorlevel 1 (
    echo ERROR: Failed to create .venv
    pause
    exit /b 1
  )
  if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv was not created correctly.
    pause
    exit /b 1
  )
  echo .venv created.
)
echo.

REM ── 2. Install / sync dependencies into .venv ─────────────────────────────
echo Checking dependencies in .venv ...
set "NEED_INSTALL=0"
if not exist ".venv\Scripts\uvicorn.exe" set "NEED_INSTALL=1"

".venv\Scripts\python.exe" -c "import fastapi,uvicorn,sqlalchemy,alembic" >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="1" (
  echo Dependencies missing or incomplete — installing into .venv ...
  echo.
  if "%HAS_UV%"=="1" (
    REM uv sync installs the project + lockfile deps into ./.venv
    uv sync
    if errorlevel 1 (
      echo ERROR: uv sync failed.
      pause
      exit /b 1
    )
  ) else (
    if not exist "requirements.txt" (
      echo ERROR: requirements.txt not found ^(needed for pip install^).
      pause
      exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
      echo ERROR: pip upgrade failed.
      pause
      exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
      echo ERROR: pip install -r requirements.txt failed.
      pause
      exit /b 1
    )
  )
  echo.
  REM Verify install landed in .venv
  if not exist ".venv\Scripts\uvicorn.exe" (
    echo ERROR: uvicorn still missing from .venv after install.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -c "import fastapi,uvicorn,sqlalchemy,alembic" >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Core packages failed to import from .venv after install.
    pause
    exit /b 1
  )
  echo Dependencies installed into .venv.
  echo.
) else (
  echo Dependencies OK in .venv.
  echo.
)

REM ── 3. Activate .venv and run API ─────────────────────────────────────────
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: Failed to activate .venv
  pause
  exit /b 1
)

echo Using: 
where python
echo.
echo Starting API on http://localhost:8010
echo Swagger: http://localhost:8010/docs
echo.
".venv\Scripts\uvicorn.exe" api.main:app --host 0.0.0.0 --port 8010 --reload --limit-concurrency 64
if errorlevel 1 (
  echo.
  echo ERROR: Server failed to start.
  pause
  exit /b 1
)

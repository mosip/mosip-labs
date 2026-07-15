@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Nexus UI — React (Vite)
echo ========================================
echo.

if not exist ".env" (
  if exist ".env.example" (
    echo Creating .env from .env.example ...
    copy /Y ".env.example" ".env" >nul
    echo.
  ) else (
    echo ERROR: .env.example not found.
    pause
    exit /b 1
  )
)

where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: npm not found. Install Node.js 20+ from https://nodejs.org
  pause
  exit /b 1
)

echo Checking npm dependencies ...
set "NEED_INSTALL=0"
if not exist "node_modules\" set "NEED_INSTALL=1"
if not exist "node_modules\.bin\vite.cmd" set "NEED_INSTALL=1"
if not exist "node_modules\react\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\react-dom\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\react-router-dom\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\react-markdown\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\remark-gfm\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\typescript\package.json" set "NEED_INSTALL=1"
if not exist "node_modules\@vitejs\plugin-react\package.json" set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="1" (
  echo Dependencies missing or incomplete — installing ...
  echo.
  if exist "package-lock.json" (
    call npm ci
  ) else (
    call npm install
  )
  if errorlevel 1 (
    echo ERROR: npm install failed.
    pause
    exit /b 1
  )
  echo.
  echo Dependencies installed.
  echo.
) else (
  echo Dependencies OK.
  echo.
)

echo Starting Vite on http://localhost:8501
echo API proxy: /api -^> value of VITE_DEV_API_PROXY in .env
echo           ^(default http://localhost:8010 — start Server\run.bat first^)
echo.
call npm run dev
if errorlevel 1 (
  echo.
  echo ERROR: Vite failed to start.
  pause
  exit /b 1
)

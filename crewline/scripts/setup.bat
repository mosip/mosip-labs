@echo off
REM One-time Crewline setup for Windows.
REM Installs Python deps, runs validator tests, checks tools.yaml, optionally installs an adapter.
REM
REM   scripts\setup.bat
REM   scripts\setup.bat cursor D:\work\mosip
REM   scripts\setup.bat claude D:\work\mosip --force
REM   scripts\setup.bat generic D:\work\pre-registration
REM
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0.."
pushd "%ROOT%" || exit /b 1
set "PLATFORM="
set "TARGET="
set "FORCE="
set "SKIP_TESTS="
set "TOOLS_RC=0"

:parse
if "%~1"=="" goto parsed
if /I "%~1"=="--help" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--force" set "FORCE=--force" & shift & goto parse
if /I "%~1"=="--skip-tests" set "SKIP_TESTS=1" & shift & goto parse
if /I "%~1"=="cursor" set "PLATFORM=cursor" & shift & goto parse
if /I "%~1"=="claude" set "PLATFORM=claude" & shift & goto parse
if /I "%~1"=="generic" set "PLATFORM=generic" & shift & goto parse
if not defined TARGET (
  set "TARGET=%~1"
  shift
  goto parse
)
echo unexpected argument: %~1
goto usage

:usage
echo Crewline setup ^(prerequisites + optional adapter^)
echo.
echo   %~nx0
echo   %~nx0 ^<cursor^|claude^|generic^> ^<target-folder^> [--force] [--skip-tests]
echo.
echo   target-folder  folder where you keep MOSIP module clones ^(Cursor/Claude^),
echo                  or the module repo itself ^(generic git hooks^)
echo.
echo This script does not install Git, GitHub CLI, or the active pack's stack
echo ^(MOSIP default: JDK 21, Maven^). Missing ones are listed with numbered
echo enable steps from core\tools.yaml + packs\ACTIVE.
popd
exit /b 2

:parsed
if defined PLATFORM if not defined TARGET (
  echo error: %PLATFORM% needs a target folder ^(where your MOSIP clones live^).
  goto usage
)

echo == Crewline setup ==
echo     core: %CD%

set "PY="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY=py -3"
  goto py_ok
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY=python"
  goto py_ok
)
python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY=python3"
  goto py_ok
)
echo error: Python 3.11+ is required and must be on PATH.
echo   1. Install Python 3.11+ from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^)
echo   2. Open a new terminal and run: python --version
echo   3. Re-run: %~f0
popd
exit /b 1

:py_ok
echo -- python:
call %PY% --version

echo -- pip install -r validators\requirements.txt
call %PY% -m pip install -r "%CD%\validators\requirements.txt"
if errorlevel 1 (
  echo error: pip install failed.
  popd
  exit /b 1
)

if defined SKIP_TESTS (
  echo -- pytest skipped (--skip-tests)
) else (
  echo -- pytest validators
  pushd "%CD%\validators"
  call %PY% -m pytest -q tests
  set "PT=!errorlevel!"
  popd
  if not "!PT!"=="0" (
    echo error: validator tests failed. Do not install the adapter until they pass.
    popd
    exit /b 1
  )
)

echo -- python -m crewline tools
pushd "%CD%\validators"
call %PY% -m crewline tools
set "TOOLS_RC=!errorlevel!"
popd
if not "!TOOLS_RC!"=="0" (
  echo.
  echo Some tools.yaml capabilities are missing. Follow the numbered enable steps above.
  echo You can still install an adapter; a task that needs a missing tool will stop at S0.
)

if defined PLATFORM (
  echo -- adapters\install.py --platform %PLATFORM% --target %TARGET% --write %FORCE%
  call %PY% "%CD%\adapters\install.py" --platform %PLATFORM% --target "%TARGET%" --write %FORCE%
  if errorlevel 1 (
    echo error: adapter install failed.
    popd
    exit /b 1
  )
  echo.
  echo Next: open %TARGET% in %PLATFORM% and describe the work in one message.
  echo       ^(Cursor or Claude Code starts the crew; this script does not.^)
) else (
  echo.
  echo Prerequisites for Crewline itself are in place ^(Python package + tests^).
  echo Install an adapter when you are ready:
  echo   %~nx0 cursor  D:\work\mosip
  echo   %~nx0 claude  D:\work\mosip
  echo   %~nx0 generic D:\work\pre-registration
)

if not "!TOOLS_RC!"=="0" (
  popd
  exit /b 2
)
echo OK
popd
exit /b 0

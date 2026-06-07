@echo off
REM ============================================================
REM Sanchay — Windows build script
REM Produces a ready-to-distribute folder at dist\Sanchay\
REM ============================================================

echo.
echo ============================
echo  Sanchay Build Script
echo ============================
echo.

REM Activate venv and run PyInstaller
call venv\Scripts\activate.bat

echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [2/3] Running PyInstaller...
pyinstaller sanchay.spec --clean -y

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo Output: dist\Sanchay\
echo   - Sanchay.exe  (launcher)
echo   - _internal\   (all dependencies, PySide6, resources)
echo.
echo Distribute the entire dist\Sanchay\ folder.
echo.
pause

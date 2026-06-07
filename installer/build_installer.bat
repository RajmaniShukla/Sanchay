@echo off
REM ============================================================
REM Sanchay — NSIS Installer Build Script
REM Run this AFTER build_exe.bat has produced dist\Sanchay\
REM ============================================================

echo.
echo ====================================
echo  Sanchay Installer Build
echo ====================================
echo.

REM Check dist exists
if not exist "..\dist\Sanchay\Sanchay.exe" (
    echo ERROR: dist\Sanchay\Sanchay.exe not found.
    echo Run build_exe.bat first.
    pause
    exit /b 1
)

REM Find makensis
set MAKENSIS=
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    set MAKENSIS="C:\Program Files (x86)\NSIS\makensis.exe"
) else if exist "C:\Program Files\NSIS\makensis.exe" (
    set MAKENSIS="C:\Program Files\NSIS\makensis.exe"
) else (
    echo ERROR: NSIS not found.
    echo Download from: https://nsis.sourceforge.io/Download
    pause
    exit /b 1
)

echo [1/2] Compiling NSIS script...
%MAKENSIS% sanchay_installer.nsi

if errorlevel 1 (
    echo.
    echo ERROR: NSIS compilation failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Installer built!
echo.
echo Output: installer\SanchaySetup-1.0.0.exe
echo.
echo Distribute this single file to end users.
echo.
pause

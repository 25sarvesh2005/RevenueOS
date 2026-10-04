@echo off
cd /d "%~dp0"
title RevenueOS Studio - Power BI Desktop Replica Engine

echo ===============================================================================
echo                RevenueOS Studio - Power BI Desktop Replica
echo          Automated Excel-to-Power BI Decision Engine and Studio
echo                    Author: Sarvesh Sharma (Royalty License)
echo ===============================================================================
echo.

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not found in your system PATH.
    echo Please install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [*] Installing required desktop dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install npm dependencies.
        pause
        exit /b 1
    )
)

echo [*] Launching RevenueOS Desktop Studio...
echo.
call npm start

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with code %errorlevel%.
    pause
)

@echo off
setlocal
title RevenueOS Studio - Power BI Desktop Replica Engine
color 0B

echo ===============================================================================
echo                RevenueOS Studio - Power BI Desktop Replica
echo          Automated Excel-to-Power BI Decision Engine & Studio
echo                    Author: Sarvesh Sharma (Royalty License)
echo ===============================================================================
echo.

:: Check Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Node.js is not found in your system PATH.
    echo Please install Node.js (v18+) to run RevenueOS Studio.
    echo Download: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: Check if node_modules exists, install if missing
if not exist "node_modules\" (
    echo [*] Installing required desktop dependencies (one-time setup)...
    call npm install
    if %errorlevel% neq 0 (
        color 0C
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
    echo [!] Application closed with code %errorlevel%.
    pause
)

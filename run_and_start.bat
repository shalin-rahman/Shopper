@echo off
setlocal

:: Attempt to kill any previously running instances of this launcher window
taskkill /F /FI "WINDOWTITLE eq *Shopper Pipeline Runner*" >nul 2>&1
title Shopper Pipeline Runner

echo ==============================================
echo Checking Docker Desktop Status...
echo ==============================================
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not found.
    echo Please start Docker Desktop and ensure it is fully running before executing this script.
    pause
    exit /b 1
)

echo ==============================================
echo Stopping any already running services...
echo ==============================================
call docker-compose down

echo ==============================================
echo [1/3] Rebuilding API Image and Running Tests (Python/FastAPI via Docker)
echo ==============================================
call docker-compose build api
call docker-compose run --rm api pytest -v
if %errorlevel% neq 0 (
    echo ==============================================
    echo API Tests Failed! Aborting...
    echo ==============================================
    pause
    exit /b %errorlevel%
)

echo ==============================================
echo [2/3] Skipping Web Tests (Angular) - Local Node.js execution policy restricted.
echo ==============================================
:: Skipping local npm tests due to powershell constraints on this machine.

echo ==============================================
echo [3/3] Skipping Mobile Tests (Flutter) - Flutter not installed globally.
echo ==============================================
:: Skipping local flutter tests due to missing path.

echo ==============================================
echo All configured tests passed successfully! Starting all apps...
echo ==============================================

:: Start Docker Compose services for Node/Python/Postgres
call docker-compose pull
call docker-compose up -d --build

echo.
echo Database, API, and Web Apps are starting via Docker Compose.
echo API: http://localhost:8000
echo Web: http://localhost (via openresty)
echo.
echo Opening browser...
start http://localhost
start http://localhost:8000/docs
echo.
echo Launching Mobile App...
start cmd /k "title Shopper Mobile Launcher && echo Starting Shopper Mobile... && cd shopper-mobile && flutter run"
echo ==============================================
echo Press any key to exit this window...
pause >nul

endlocal

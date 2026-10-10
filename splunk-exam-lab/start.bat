@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Install Python 3.10 or newer. & exit /b 1)
where node >nul 2>nul || (echo Install Node.js 20.19+ and pnpm. & exit /b 1)
where pnpm >nul 2>nul || (echo Install pnpm with npm install -g pnpm & exit /b 1)
if not exist backend\.venv py -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
pushd frontend
call pnpm install --frozen-lockfile
if errorlevel 1 exit /b 1
popd
pushd backend
.venv\Scripts\python.exe -m app.seed
if errorlevel 1 exit /b 1
start "Splunk Lab API - close to stop" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
popd
pushd frontend
echo Open http://127.0.0.1:5173 in your browser.
call pnpm dev
popd

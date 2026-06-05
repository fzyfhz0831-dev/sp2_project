@echo off
REM --- Configuration ---
set FRONTEND_PATH=C:\Users\24364\sp2_project\sp2-frontend
set JSON_FILE=C:\Users\24364\sp2_project\sp2-backend\sample_run.json
set API_URL=https://sp2-project-1.onrender.com/api/analyze
set DEPLOY_HOOK=https://api.render.com/deploy/srv-d8gqha0jo6nc73esho30?key=oVxTHK3xZ5g

REM --- 1. Modify frontend API URL ---
echo Modifying frontend API URL...
powershell -Command "(Get-Content '%FRONTEND_PATH%\src\main.js') -replace 'const API_URL = .*', 'const API_URL = \"%API_URL%\"' | Set-Content '%FRONTEND_PATH%\src\main.js' -Encoding UTF8"

REM --- 2. Build frontend ---
echo Building frontend project...
cd %FRONTEND_PATH%
npm install
npm run build

REM --- 3. Trigger Render frontend deploy ---
echo Triggering Render frontend deploy...
powershell -Command "Invoke-RestMethod -Uri '%DEPLOY_HOOK%' -Method Post"

REM --- 4. Upload JSON to backend API ---
echo Uploading JSON file for analysis...
python -c "import requests; f=open(r'%JSON_FILE%', 'rb'); r=requests.post(r'%API_URL%', files={'file': f}); f.close(); print(r.text)"

echo.
echo Done.
pause
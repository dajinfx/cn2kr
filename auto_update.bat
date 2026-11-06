@echo off
chcp 65001 >nul
setlocal

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set PYTHON=D:\Application\python3.10\python.exe
set LOG=D:\Git\cn2kr\auto_update.log

echo [%date% %time%] ===== cn2kr daily update START ===== >> "%LOG%"

cd /d D:\Git\cn2kr\pipeline

echo --- Generating content --- >> "%LOG%"
%PYTHON% pipeline.py --category tech --count 1 >> "%LOG%" 2>&1
%PYTHON% pipeline.py --category travel --count 1 >> "%LOG%" 2>&1
%PYTHON% pipeline.py --category direct --count 1 >> "%LOG%" 2>&1

echo --- Fetching images --- >> "%LOG%"
%PYTHON% fetch_images.py >> "%LOG%" 2>&1

echo --- Committing and pushing --- >> "%LOG%"
cd /d D:\Git\cn2kr
git add -A >> "%LOG%" 2>&1
git commit -m "auto: daily content update (%date%)" >> "%LOG%" 2>&1
git push >> "%LOG%" 2>&1

echo [%date% %time%] ===== cn2kr daily update DONE ===== >> "%LOG%"
echo.
endlocal

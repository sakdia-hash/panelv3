@echo off
title Instagram Takipci Sistemi - Baslatiliyor
echo ==========================================
echo 1. Kutuphaneler yukleniyor (backend)...
echo ==========================================
python -m pip install -r backend/requirements.txt

echo.
echo ==========================================
echo 2. Veritabani ve Admin hesabi olusturuluyor...
echo ==========================================
python -m backend.seed

echo.
echo ==========================================
echo 3. Sunucu baslatiliyor...
echo ==========================================
echo.
echo Tarayiciyi ac: http://localhost:8000
echo.
echo Backend Sunucusu: http://0.0.0.0:8000
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause

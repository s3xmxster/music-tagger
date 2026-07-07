@echo off
setlocal

if not exist venv (
    echo [INFO] Виртуальное окружение не найдено.
    echo [INFO] Создаю venv...
    py -m venv venv
)

call venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "Music Tagger" ^
  --icon "assets\app_exe.ico" ^
  --add-data "config.json;." ^
  --add-data "assets;assets" ^
  main.py

echo.
echo [DONE] Сборка завершена.
echo Готовое приложение: dist\Music Tagger\
pause
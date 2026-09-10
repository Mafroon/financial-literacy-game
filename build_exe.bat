@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Сборка игры "Финансовая Грамотность"
echo ============================================
echo.

REM --- ищем главный файл ---
set SCRIPT=main.py
if not exist "%SCRIPT%" set SCRIPT=main.pyw
if not exist "%SCRIPT%" (
    echo [ОШИБКА] Не найден main.py или main.pyw
    pause
    exit /b 1
)
echo [1/3] Главный файл найден: %SCRIPT%

REM --- проверяем Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo        При установке Python отметьте галочку "Add Python to PATH",
    echo        затем перезагрузите компьютер.
    pause
    exit /b 1
)

echo [2/3] Устанавливаю PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить PyInstaller. Проверьте интернет.
    pause
    exit /b 1
)

echo [3/3] Собираю exe (это займет 1-2 минуты)...
python -m PyInstaller --onefile --windowed --clean --noconfirm ^
    --name "Финансовая Грамотность" ^
    --icon icon.ico ^
    --add-data "assets;assets" ^
    "%SCRIPT%"
if errorlevel 1 (
    echo [ОШИБКА] Сборка не удалась — прочтите сообщения выше.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ГОТОВО!
echo   Игра: dist\Финансовая Грамотность.exe
echo ============================================
pause

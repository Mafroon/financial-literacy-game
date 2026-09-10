"""Глобальные константы, настройки окна, цвета, шрифты и игровые данные.

Импортируется первым — выполняет pygame.init() и создаёт окно.
Остальные модули берут отсюда общие настройки, не дублируя их.

Каталоги предметов и тестов живут в db.py (ITEM_CATALOG, TEST_CATALOG) —
это единственный источник правды, они же засевают БД. Здесь они
импортируются и превращаются в производные списки для UI — вручную
ничего не дублируем.
"""

import os
import sys
import pygame

import db  # чистый слой данных: без pygame, импорт безопасен

pygame.init()

# --- Пути -------------------------------------------------------------------
def resource_path(*parts):
    """Путь к ресурсу: рядом со скриптом при разработке,
    внутри архива PyInstaller (sys._MEIPASS) в собранном .exe."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = resource_path('assets')

# --- Окно -------------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Иконка окна (заголовок + панель задач)
try:
    pygame.display.set_icon(pygame.image.load(resource_path('assets', 'icon.png')))
except pygame.error:
    pass

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Финансовая Грамотность")

# --- Цвета ------------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
PEACH_COLOR = (255, 218, 185)
LIGHT_GREEN = (144, 238, 144)
BUTTON_COLOR = (70, 130, 180)
HIGHLIGHT_COLOR = (100, 149, 237)
SEMI_TRANSPARENT = (0, 0, 0, 128)
BUTTON_BG = (255, 255, 255, 50)
PHONE_BG = (255, 255, 255, 50)
NOBLE_BLUE = (70, 130, 180, 128)

# --- Шрифты -----------------------------------------------------------------
font = pygame.font.Font(None, 36)
result_font = pygame.font.Font(None, 48)
currency_font = pygame.font.Font(None, 72)
energy_font = pygame.font.Font(None, 48)
status_font = pygame.font.Font(None, 36)
day_font = pygame.font.Font(None, 72)
date_font = pygame.font.Font(None, 36)
fade_day_font = pygame.font.Font(None, 120)
fade_rouns_font = pygame.font.Font(None, 60)
fail_font = pygame.font.Font(None, 100)
confirm_font = pygame.font.Font(None, 48)

# --- Календарь --------------------------------------------------------------
BASE_DATE = (2025, 1, 1)
MONTH_NAMES = ["янв.", "фев.", "мар.", "апр.", "мая", "июн.",
               "июл.", "авг.", "сен.", "окт.", "ноя.", "дек."]


def get_date(day: int) -> str:
    """Возвращает строку вида '15 янв. 2025 г.' для игрового дня (отсчёт с BASE_DATE)."""
    year, month = BASE_DATE[0], BASE_DATE[1] - 1
    day_count = day - 1
    days_in_year_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    while day_count > 0:
        days_in_month = days_in_year_month[month]
        if month == 1 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
            days_in_month = 29
        if day_count >= days_in_month:
            day_count -= days_in_month
            month = (month + 1) % 12
            if month == 0:
                year += 1
        else:
            break
    return f"{day_count + 1} {MONTH_NAMES[month]} {year} г."


# --- Отображаемые имена для пола --------------------------------------------
GENDER_DISPLAY = {
    'male': 'мужской',
    'female': 'женский',
}

# --- Отображаемые имена предметов -------------------------------------------
ITEM_DISPLAY_NAMES = {
    'male_hair1': 'Взлохмаченная',
    'male_hair2': 'Короткая стрижка',
    'male_hair3': 'Уложенные волосы',
    'female_hair1': 'Хвостик',
    'female_hair2': 'Короткая стрижка',
    'female_hair3': 'Длинные волосы',
    'male_clothes1': 'Базовый',
    'male_clothes2': 'Повседневный',
    'male_clothes3': 'Спортивный',
    'male_clothes4': 'Классический',
    'female_clothes1': 'Базовый',
    'female_clothes2': 'Повседневный',
    'female_clothes3': 'Спортивный',
    'female_clothes4': 'Классический',
}

# --- Производные от каталогов db.py (не дублировать вручную!) ---------------
# Магазин: все не-default предметы из db.ITEM_CATALOG
PURCHASABLE_ITEMS = [
    {"name": name, "type": type_, "gender": gender, "price": price, "image": image}
    for name, type_, gender, price, image, is_default in db.ITEM_CATALOG
    if not is_default
]

# Тесты: TEST_COSTS[i] — цена теста (i+1); TEST_REWARDS[test_num] — награда
_sorted_tests = sorted(db.TEST_CATALOG)
TEST_COSTS = [cost for _, _, cost, _ in _sorted_tests]
TEST_REWARDS = [0] + [reward for _, _, _, reward in _sorted_tests]

# --- Экономика --------------------------------------------------------------
START_ROUNS = 500            # стартовый капитал нового игрока (единственный источник правды)
STATUS_BONUSES = {
    "Новичок": 0, "Эконом": 50, "Накопитель": 100, "Инвестор": 200,
    "Стратег": 350, "Эксперт": 500, "Магнат": 800, "Мудрец": 1200,
}
STATUSES = list(STATUS_BONUSES)          # порядок важен: индекс = passed_tests

WORK_ENERGY_COST = 3
WORK_BASE_MIN, WORK_BASE_MAX = 150, 300
LEARN_ENERGY_COST = 2
FOOD_MIN, FOOD_MAX = 100, 300
UTILITIES_COST = 1500
UTILITIES_DAY = 10           # коммуналка списывается каждое 10-е число
MAX_ENERGY = 5
QUESTIONS_PER_TEST = 10

TAX_DAILY = 500              # ежемесячный налог (20-е число, см. fade_screen)
HOLIDAY_DATES = ["31 дек.", "23 фев.", "8 мар.", "1 мая",
                 "9 мая", "12 июн.", "4 ноя."]   # праздники: двойные траты на еду

# Стипендия за учёбу
LESSONS_PER_STIPEND = 5
STIPEND_AMOUNT = 600

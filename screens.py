"""Игровые экраны и главный цикл интерфейса.

Каждый экран — функция, которая крутит свой цикл событий и возвращает
управление вызывающей стороне (никакой рекурсии между экранами):

    main_menu()              — главное меню (играть / сброс / выход)
    avatar_creation_screen() — создание персонажа
    game_screen()            — комната: работа, учёба, сон, телефон
    phone_screen()           — телефон → магазин
    inventory_screen()       — выбор внешности
    fade_screen()            — переход ко сну: списания и новый день
"""

import os
import random
import sys
import pygame

import db
from constants import (
    screen, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, ASSETS_DIR,
    WHITE, BLACK, GRAY, RED, ORANGE,
    SEMI_TRANSPARENT, PHONE_BG, NOBLE_BLUE, BUTTON_COLOR,
    font, currency_font, energy_font, status_font,
    day_font, date_font, fade_day_font, fade_rouns_font, fail_font,
    get_date,
    TEST_COSTS, STATUS_BONUSES,
    WORK_ENERGY_COST, WORK_BASE_MIN, WORK_BASE_MAX,
    LEARN_ENERGY_COST, FOOD_MIN, FOOD_MAX,
    UTILITIES_COST, UTILITIES_DAY, MAX_ENERGY,
    ITEM_DISPLAY_NAMES, GENDER_DISPLAY,
    TAX_DAILY, HOLIDAY_DATES,
)
from content_texts import TOPIC_TEXTS, HELP_TEXT
from entities import Avatar, AvatarCreator, Inventory
from ui import (
    Button, GameScreen, draw_outlined,
    ButtonOverlay, TextOverlay, TestOverlay,
    PhoneOverlay, StoreOverlay, ConfirmResetOverlay,
    HelpOverlay,
)

hud_messages = GameScreen()


def _load_asset(name, size=None):
    """Загружает ассет; при отсутствии — None (рисуется заглушка)."""
    try:
        image = pygame.image.load(os.path.join(ASSETS_DIR, name))
        return pygame.transform.scale(image, size) if size else image
    except pygame.error:
        return None


def _dim_screen():
    dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    dim.fill(SEMI_TRANSPARENT)
    screen.blit(dim, (0, 0))


# ------------------------------------------------------------------- HUD

def _panel_with_text(screen_, text_surface, position, outline=True):
    """Текст на полупрозрачной панели с чёрной обводкой."""
    rect = text_surface.get_rect(topleft=position)
    panel_rect = rect.inflate(10, 10)
    panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    panel.fill(SEMI_TRANSPARENT)
    screen_.blit(panel, panel_rect.topleft)
    if outline:
        draw_outlined(screen_, text_surface, position)
    screen_.blit(text_surface, position)


def draw_hud(screen_, avatar):
    """Вся статистика по углам: день, дата, ник, рубли, энергия, статус."""
    draw_day(screen_, avatar)
    draw_rouns(screen_, avatar)


def draw_rouns(screen_, avatar):
    _panel_with_text(screen_, currency_font.render(f"Рубли: {avatar.rouns}", True, WHITE),
                     (SCREEN_WIDTH - 400, 10))
    _panel_with_text(screen_, energy_font.render(f"Энергия: {avatar.energy}/{MAX_ENERGY}", True, WHITE),
                     (SCREEN_WIDTH - 350, 90))
    _panel_with_text(screen_, status_font.render(f"Статус: {avatar.status}", True, WHITE),
                     (SCREEN_WIDTH - 350, 150))


def draw_day(screen_, avatar):
    _panel_with_text(screen_, day_font.render(f"День {avatar.current_day}", True, WHITE),
                     (10, 10))
    _panel_with_text(screen_, date_font.render(get_date(avatar.current_day), True, GRAY),
                     (10, 92))
    day_panel_right = 10 + day_font.size(f"День {avatar.current_day}")[0] + 30
    _panel_with_text(screen_, status_font.render(f"Имя: {avatar.nickname}", True, WHITE),
                     (day_panel_right, 10))


# ------------------------------------------------------------ сцена комнаты

class RoomScene:
    """Единая отрисовка комнаты: фон, аватар, кнопки, телефон, HUD.

    Раньше сцена рисовалась в двух местах с разными координатами —
    теперь источник один.
    """

    def __init__(self, avatar):
        self.avatar = avatar
        self.background = _load_asset('room_background.png')
        self.phone = _load_asset('phone.png', (150, 150))
        self.phone_rect = (self.phone.get_rect(topleft=(20, SCREEN_HEIGHT - 170))
                           if self.phone else pygame.Rect(20, SCREEN_HEIGHT - 170, 150, 150))
        self.buttons = self._make_buttons()

    @staticmethod
    def _make_buttons():
        return {
            'learn': Button(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 170, 170, 50,
                            "Учиться", action="learn"),
            'inventory': Button(SCREEN_WIDTH * 3 // 4 - 300, SCREEN_HEIGHT // 2 + 25, 200, 50,
                                "Инвентарь", action="inventory"),
            'sleep': Button(SCREEN_WIDTH // 4 - 230, SCREEN_HEIGHT // 2 + 25, 150, 50,
                            "Спать", action="sleep"),
            'test': Button(SCREEN_WIDTH * 3 // 4 - 50, SCREEN_HEIGHT // 2 - 50, 230, 50,
                           "Проверить знания", action="test"),
            'work': Button(SCREEN_WIDTH * 3 // 4 - 50, SCREEN_HEIGHT // 2 + 10, 170, 50,
                           "Работать", action="work"),
            'menu': Button(SCREEN_WIDTH - 210, SCREEN_HEIGHT - 110, 200, 50,
                           "Меню", action="menu"),
            'help': Button(SCREEN_WIDTH - 210, SCREEN_HEIGHT - 170, 200, 50,
                           "Помощь", action="help"),
        }

    def draw(self, screen_):
        if self.background:
            screen_.blit(self.background, (0, 0))
        else:
            screen_.fill(WHITE)
        self.avatar.draw(screen_, (SCREEN_WIDTH // 4 - 200, SCREEN_HEIGHT // 2 - 315))
        for button in self.buttons.values():
            button.draw(screen_)
        self._draw_phone(screen_)
        draw_hud(screen_, self.avatar)
        hud_messages.draw(screen_)

    def _draw_phone(self, screen_):
        if self.phone:
            panel_rect = self.phone_rect.inflate(10, 10)
            panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            hovered = self.phone_rect.collidepoint(pygame.mouse.get_pos())
            panel.fill(NOBLE_BLUE if hovered else PHONE_BG)
            screen_.blit(panel, panel_rect.topleft)
            screen_.blit(self.phone, self.phone_rect)
        else:
            pygame.draw.rect(screen_, GRAY, self.phone_rect)
            screen_.blit(font.render("Телефон", True, BLACK), self.phone_rect.topleft)


# ------------------------------------------------------------- сон / новый день

def fade_screen(avatar, food_deduction):
    """Затемнение, списание еды, коммуналки, налога, праздничных трат, новый день.
    
    При банкротстве — экран «Провал» и сброс сохранения.
    """
    next_day = avatar.current_day + 1
    date_str = get_date(next_day)
    day_num = int(date_str.split()[0])
    
    # --- Расчёт списаний ---
    total_deduction = food_deduction          # базовые расходы на еду
    extra_food = 0
    holiday_multiplier = 1
    
    # Проверка праздничного дня
    current_date_str = get_date(avatar.current_day)
    current_day_num = int(current_date_str.split()[0])
    current_month = current_date_str.split()[1]
    current_holiday_str = f"{current_day_num} {current_month}"
    if current_holiday_str in HOLIDAY_DATES:
        holiday_multiplier = 2
        extra_food = food_deduction
        total_deduction += extra_food
    
    # Коммунальные услуги (10-е число)
    utilities = UTILITIES_COST if day_num == UTILITIES_DAY else 0
    if utilities:
        total_deduction += utilities
    
    # Ежемесячный налог (20-е число)
    tax = TAX_DAILY if day_num == 20 else 0
    if tax:
        total_deduction += tax
    
    avatar.rouns -= total_deduction
    failed = avatar.rouns <= 0
    avatar.save_to_db()
    
    # --- Координаты для отображения ---
    center_x = SCREEN_WIDTH // 2
    day_y = SCREEN_HEIGHT // 2 - 150
    food_y = day_y + 100
    extra_y = food_y + 50
    utilities_y = extra_y + 50 if holiday_multiplier > 1 else food_y + 50
    tax_y = utilities_y + 50 if utilities else (extra_y + 50 if holiday_multiplier > 1 else food_y + 50)
    remaining_y = tax_y + 50 if tax else (utilities_y + 50 if utilities else (extra_y + 50 if holiday_multiplier > 1 else food_y + 50))
    fail_y = remaining_y + 70
    button_y = fail_y + 50 if failed else remaining_y + 50
    
    # --- Сборка строк для отображения ---
    labels = [
        (fade_day_font, f"День {next_day}", WHITE, day_y),
        (fade_rouns_font, f"Еда: -{food_deduction} рублей", ORANGE, food_y),
    ]
    
    if holiday_multiplier > 1:
        labels.append((fade_rouns_font, f"Праздничные траты: -{extra_food} рублей", ORANGE, extra_y))
    
    if utilities:
        labels.append((fade_rouns_font, f"Коммунальные услуги: -{utilities} рублей", ORANGE, utilities_y))
    
    if tax:
        labels.append((fade_rouns_font, f"Налог: -{tax} рублей", ORANGE, tax_y))
    
    labels.append((fade_rouns_font, f"Осталось: {avatar.rouns} рублей", WHITE, remaining_y))
    
    if failed:
        labels.append((fail_font, "Провал", RED, fail_y))
    
    button = Button(center_x - 100, button_y, 200, 50,
                    "Выйти из игры" if failed else "Далее")
    
    # --- Затемнение ---
    fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade.fill(BLACK)
    for alpha in range(0, 255, 5):
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.flip()
        pygame.time.wait(10)
    
    # --- Ожидание нажатия ---
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEMOTION:
                button.hovered = button.rect.collidepoint(event.pos)
            if (event.type == pygame.MOUSEBUTTONDOWN
                    and button.rect.collidepoint(event.pos)):
                if failed:
                    db.reset_save()
                    pygame.quit()
                    sys.exit()
                avatar.current_day += 1
                avatar.save_to_db()
                return
        
        screen.fill(BLACK)
        for font_, text, color, y in labels:
            surface = font_.render(text, True, color)
            draw_outlined(screen, surface, surface.get_rect(center=(center_x, y)))
        button.draw(screen)
        pygame.display.flip()


# ----------------------------------------------------------------- главное меню

def main_menu():
    """Главное меню. Выходит из функции только при завершении игры."""
    avatar = Avatar()
    buttons = {
        'start': Button((SCREEN_WIDTH - 210) // 2, 250, 210, 50,
                        "Играть", action="start_game"),
        'reset': Button((SCREEN_WIDTH - 210) // 2, 350, 210, 50,
                        "Сброс прогресса", action="reset"),
        'quit': Button((SCREEN_WIDTH - 210) // 2, 450, 210, 50,
                       "Выход", action="quit"),
    }
    overlay = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                pygame.quit()
                sys.exit()
            if overlay:
                action = overlay.handle_event(event)
                if action == "confirm_reset":
                    overlay = None
                    pygame.display.flip()
                    db.reset_save()
                    avatar = Avatar()
                elif action == "cancel":
                    overlay = None
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons.values():
                    if button.rect.collidepoint(event.pos):
                        if button.action == "start_game":
                            if avatar.avatar_created:
                                game_screen(avatar)
                            else:
                                avatar_creation_screen(avatar)
                        elif button.action == "reset":
                            overlay = ConfirmResetOverlay()
                        elif button.action == "quit":
                            avatar.save_to_db()
                            pygame.quit()
                            sys.exit()
            elif event.type == pygame.MOUSEMOTION:
                for button in buttons.values():
                    button.hovered = button.rect.collidepoint(event.pos)

        screen.fill(WHITE)
        for button in buttons.values():
            button.draw(screen)
        if overlay:
            _dim_screen()
            overlay.draw(screen)
        pygame.display.flip()


# --------------------------------------------------------- создание персонажа

def avatar_creation_screen(avatar):
    creator = AvatarCreator(avatar)
    buttons = {
        'gender_prev': Button(100, 550, 100, 50, "<"),
        'gender_next': Button(220, 550, 100, 50, ">"),
        'hair_prev': Button(900, 450, 100, 50, "<"),
        'hair_next': Button(1020, 450, 100, 50, ">"),
        'clothes_prev': Button(900, 550, 100, 50, "<"),
        'clothes_next': Button(1020, 550, 100, 50, ">"),
        'back': Button(50, 50, 100, 40, "Назад", action="back"),
    }

    while True:
        screen.fill(WHITE)
        selection = creator.get_current_selection()

        creator.draw_avatar(screen, selection['gender'], selection)
        pygame.draw.rect(screen, GRAY, creator.input_rect)
        screen.blit(font.render(creator.nickname_input, True, BLACK),
                    (creator.input_rect.x + 5, creator.input_rect.y + 5))
        screen.blit(font.render("Введите имя (3-15 символов)", True, BLACK),
                    (100, 260))

        gender_display = GENDER_DISPLAY.get(selection['gender'], selection['gender'])
        gender_label = f"Пол: {gender_display}"
        hair_display = ITEM_DISPLAY_NAMES.get(selection['hair'], selection['hair'])
        clothes_display = ITEM_DISPLAY_NAMES.get(selection['clothes'], selection['clothes'])
        screen.blit(font.render(gender_label, True, BLACK), (100, 500))
        screen.blit(font.render(f"Прическа: {hair_display}", True, BLACK), (900, 400))
        screen.blit(font.render(f"Одежда: {clothes_display}", True, BLACK), (900, 500))

        creator.continue_button.color = BUTTON_COLOR if creator.can_continue() else GRAY
        creator.continue_button.draw(screen)
        creator.confirm_button.draw(screen)
        for button in buttons.values():
            button.draw(screen)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                creator.type_character(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if creator.confirm_button.rect.collidepoint(event.pos):
                    creator.confirm_nickname()
                elif creator.continue_button.rect.collidepoint(event.pos):
                    if creator.can_continue():
                        creator.save()
                        game_screen(avatar)
                        return
                elif buttons['back'].rect.collidepoint(event.pos):
                    return
                else:
                    for part in ('gender', 'hair', 'clothes'):
                        if buttons[f'{part}_prev'].rect.collidepoint(event.pos):
                            creator.cycle(part, 'prev')
                        elif buttons[f'{part}_next'].rect.collidepoint(event.pos):
                            creator.cycle(part, 'next')
            if event.type == pygame.MOUSEMOTION:
                for button in buttons.values():
                    button.hovered = button.rect.collidepoint(event.pos)
                creator.confirm_button.hovered = \
                    creator.confirm_button.rect.collidepoint(event.pos)
                creator.continue_button.hovered = \
                    creator.continue_button.rect.collidepoint(event.pos)


# --------------------------------------------------------------- инвентарь

def inventory_screen(avatar):
    inventory = Inventory(avatar)
    buttons = {
        'hair_prev': Button(300, 600, 100, 50, "<"),
        'hair_next': Button(420, 600, 100, 50, ">"),
        'clothes_prev': Button(800, 600, 100, 50, "<"),
        'clothes_next': Button(920, 600, 100, 50, ">"),
        'save': Button(1000, 50, 200, 50, "Сохранить", action="save"),
        'back': Button(50, 50, 100, 40, "Назад", action="back"),
    }

    while True:
        screen.fill(WHITE)
        inventory.draw(screen)
        selection = inventory.get_current_selection()

        hair_display = ITEM_DISPLAY_NAMES.get(selection['hair'], selection['hair'])
        clothes_display = ITEM_DISPLAY_NAMES.get(selection['clothes'], selection['clothes'])
        screen.blit(font.render(f"Прическа: {hair_display}", True, BLACK), (300, 550))
        screen.blit(font.render(f"Одежда: {clothes_display}", True, BLACK), (800, 550))

        for button in buttons.values():
            button.draw(screen)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if buttons['save'].rect.collidepoint(event.pos):
                    inventory.save()
                    return
                if buttons['back'].rect.collidepoint(event.pos):
                    return
                for part in ('hair', 'clothes'):
                    if buttons[f'{part}_prev'].rect.collidepoint(event.pos):
                        inventory.cycle(part, 'prev')
                    elif buttons[f'{part}_next'].rect.collidepoint(event.pos):
                        inventory.cycle(part, 'next')
            if event.type == pygame.MOUSEMOTION:
                for button in buttons.values():
                    button.hovered = button.rect.collidepoint(event.pos)


# ------------------------------------------------------------------- телефон

def phone_screen(avatar):
    """Экран телефона со стеком оверлеев (телефон → магазин)."""
    overlay_stack = [PhoneOverlay(avatar)]
    scene = RoomScene(avatar)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                pygame.quit()
                sys.exit()
            action = overlay_stack[-1].handle_event(event)
            if action == 'back':
                if len(overlay_stack) > 1:
                    overlay_stack.pop()
                else:
                    return
            elif action == 'open_store':
                overlay_stack.append(StoreOverlay(avatar))

        scene.draw(screen)
        _dim_screen()
        overlay_stack[-1].draw(screen)
        pygame.display.flip()


# --------------------------------------------------------------- игровой экран

def game_screen(avatar):
    """Комната игрока: главный игровой цикл."""
    scene = RoomScene(avatar)
    overlay_stack = []
    clock = pygame.time.Clock()

    def open_overlay(action):
        if action in ('open_budgeting', 'open_investments',
                      'open_loans', 'open_taxes'):
            topic = action.split('_')[1]
            overlay_stack.append(TextOverlay(TOPIC_TEXTS[topic], avatar))
        elif action.startswith('test') and action[4:].isdigit():
            overlay_stack.append(TestOverlay(int(action[4:]), avatar))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                avatar.save_to_db()
                return
            if overlay_stack:
                action = overlay_stack[-1].handle_event(event)
                if action == 'back':
                    overlay_stack.pop()
                elif action:
                    open_overlay(action)
                continue
            if event.type == pygame.MOUSEMOTION:
                for button in scene.buttons.values():
                    button.hovered = button.rect.collidepoint(event.pos)
                continue
            result = handle_room_event(event, avatar, scene)
            if result is None:
                continue
            kind, payload = result
            if kind == 'overlay':
                overlay_stack.append(payload)
            elif kind == 'screen':
                if payload == 'phone':
                    phone_screen(avatar)
                elif payload == 'inventory':
                    inventory_screen(avatar)
            elif kind == 'menu':
                avatar.save_to_db()
                return

        scene.draw(screen)
        if overlay_stack:
            _dim_screen()
            overlay_stack[-1].draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


def handle_room_event(event, avatar, scene):
    """Обработка клика по комнате.

    Возвращает ('overlay', оверлей) | ('screen', 'phone'|'inventory')
    | ('menu', None) | None.
    """
    if event.type != pygame.MOUSEBUTTONDOWN:
        return None
    if scene.phone_rect.collidepoint(event.pos):
        return ('screen', 'phone')
    for button in scene.buttons.values():
        if not button.rect.collidepoint(event.pos):
            continue
        if button.action == "learn" and avatar.energy >= LEARN_ENERGY_COST:
            topics = [("Бюджетирование", 'open_budgeting'),
                      ("Инвестиции", 'open_investments'),
                      ("Кредиты", 'open_loans'),
                      ("Налоги", 'open_taxes')]
            return ('overlay', ButtonOverlay(topics, avatar,
                                             energy_cost=LEARN_ENERGY_COST))
        if button.action == "inventory":
            return ('screen', 'inventory')
        if button.action == "sleep":
            avatar.energy = MAX_ENERGY
            avatar.save_to_db()
            fade_screen(avatar, random.randint(FOOD_MIN, FOOD_MAX))
            return None
        if button.action == "test":
            tests = [("Эконом", 'test1'), ("Накопитель", 'test2'),
                     ("Инвестор", 'test3'), ("Стратег", 'test4'),
                     ("Эксперт", 'test5'), ("Магнат", 'test6'),
                     ("Мудрец", 'test7')]
            buttons = [(f"Тест {i}: {title}", action)
                       for i, (title, action) in enumerate(tests, start=1)]
            return ('overlay', ButtonOverlay(buttons, avatar,
                                             energy_cost=0, test_costs=TEST_COSTS))
        if button.action == "work" and avatar.energy >= WORK_ENERGY_COST:
            do_work(avatar, button)
            return None
        if button.action == "menu":
            return ('menu', None)
        if button.action == "help":
            return ('overlay', HelpOverlay(HELP_TEXT))
    return None


def do_work(avatar, button):
    """Работа: тратит энергию, начисляет рубли с бонусом статуса."""
    avatar.energy = max(0, avatar.energy - WORK_ENERGY_COST)
    base = random.randint(WORK_BASE_MIN, WORK_BASE_MAX)
    bonus = STATUS_BONUSES[avatar.status]
    earned = base * (100 + bonus) // 100
    avatar.rouns += earned
    avatar.save_to_db()
    hud_messages.add_message(
        f"+{earned} рублей",
        (button.rect.x, button.rect.y + button.rect.height + 10))

"""UI-слой: виджеты и оверлейные окна.

Иерархия:
    GameScreen          — временные всплывающие сообщения
    Button              — кнопка (прямоугольная или круглая)
    OverlayWindow       — базовое окно поверх сцены (затемнение + кнопка «Назад»)
        ButtonOverlay   — меню из кнопок (темы обучения / список тестов)
        TextOverlay     — прокручиваемый текстовый экран
        TestOverlay     — прохождение теста (10 вопросов)
        PhoneOverlay    — экран телефона
        StoreOverlay    — магазин предметов
    ConfirmResetOverlay — подтверждение сброса прогресса
"""

import os
import random
import pygame

from constants import (
    ASSETS_DIR, SCREEN_WIDTH, SCREEN_HEIGHT,
    BLACK, WHITE, RED, PEACH_COLOR, LIGHT_GREEN,
    BUTTON_COLOR, HIGHLIGHT_COLOR, BUTTON_BG,
    font, result_font, confirm_font,
    PURCHASABLE_ITEMS, TEST_REWARDS,
    QUESTIONS_PER_TEST,
    ITEM_DISPLAY_NAMES,
    LESSONS_PER_STIPEND,
    STIPEND_AMOUNT,
)
from content_questions import QUESTIONS


# ---------------------------------------------------------------------- текст

def wrap_text(text, font_, max_width):
    """Переносит текст по ширине max_width, сохраняя разбиение на абзацы."""
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('')
            continue
        current_line = []
        for word in paragraph.split(' '):
            candidate = ' '.join(current_line + [word])
            if font_.size(candidate)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
    return lines


def draw_outlined(screen, text_surface, position, outline_color=BLACK, offset=1):
    """Рисует текст с чёрной обводкой (читаемость на любом фоне)."""
    if isinstance(position, pygame.Rect):
        x, y = position.topleft
    else:
        x, y = position
    for dx in (-offset, offset):
        for dy in (-offset, offset):
            screen.blit(text_surface, (x + dx, y + dy))


# --------------------------------------------------------------------- кнопка

class Button:
    """Прямоугольная или круглая кнопка с подсветкой при наведении."""

    def __init__(self, x, y, width, height, text, action=None,
                 color=BUTTON_COLOR, is_circle=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.color = color
        self.is_circle = is_circle
        self.hovered = False
        self.visible = True
        self.center = (x + width // 2, y + height // 2)
        self.radius = min(width, height) // 2

    def is_clicked(self, pos):
        """Проверка клика с учётом формы кнопки."""
        if self.is_circle:
            distance = ((pos[0] - self.center[0]) ** 2 +
                        (pos[1] - self.center[1]) ** 2) ** 0.5
            return distance <= self.radius
        return self.rect.collidepoint(pos)

    def draw(self, screen, offset=(0, 0)):
        if not self.visible:
            return
        if self.is_circle:
            pos = (self.center[0] + offset[0], self.center[1] + offset[1])
            color = HIGHLIGHT_COLOR if self.hovered else BUTTON_BG
            pygame.draw.circle(screen, color, pos, self.radius)
            pygame.draw.circle(screen, BLACK, pos, self.radius, 2)
            text_surface = font.render(self.text, True, WHITE)
            screen.blit(text_surface, text_surface.get_rect(center=pos))
        else:
            rect = self.rect.move(offset)
            surface = pygame.Surface((self.rect.width, self.rect.height),
                                     pygame.SRCALPHA)
            color = HIGHLIGHT_COLOR if self.hovered else self.color
            pygame.draw.rect(surface, color,
                             (0, 0, self.rect.width, self.rect.height),
                             border_radius=10)
            text_surface = font.render(self.text, True, WHITE)
            text_rect = text_surface.get_rect(
                center=(self.rect.width // 2, self.rect.height // 2))
            draw_outlined(surface, font.render(self.text, True, BLACK),
                          text_rect, offset=1)
            surface.blit(text_surface, text_rect)
            screen.blit(surface, rect)


# ------------------------------------------------------- всплывающие сообщения

class GameScreen:
    """Показывает временные сообщения (например, '+750 рублей' после работы)."""

    def __init__(self):
        self.messages = []

    def add_message(self, text, position, duration=2000):
        self.messages.append({
            'text': text, 'position': position,
            'duration': duration,
            'start_time': pygame.time.get_ticks(),
        })

    def draw(self, screen):
        now = pygame.time.get_ticks()
        for message in self.messages[:]:
            elapsed = now - message['start_time']
            if elapsed >= message['duration']:
                self.messages.remove(message)
                continue
            alpha = 255 - int(elapsed / message['duration'] * 255)
            surface = font.render(message['text'], True, WHITE)
            surface.set_alpha(alpha)
            screen.blit(surface, message['position'])


# ---------------------------------------------------------------- оверлеи

class OverlayWindow:
    """Базовое модальное окно: полупрозрачный фон + кнопка «Назад»."""

    def __init__(self, width=None, height=None, back_text="Назад"):
        self.width = width or int(SCREEN_WIDTH * 0.8)
        self.height = height or int(SCREEN_HEIGHT * 0.8)
        self.pos = ((SCREEN_WIDTH - self.width) // 2,
                    (SCREEN_HEIGHT - self.height) // 2)
        self.margin = 20
        self.back_button = Button(
            (self.width - 200) // 2, self.height - 60, 200, 50,
            back_text, action='back')

    # --- отрисовка ---------------------------------------------------------
    def draw(self, screen):
        self.draw_content(screen)
        self.back_button.draw(screen, self.pos)

    def draw_content(self, screen):
        """Сцена окна без базовой кнопки — переопределяется наследниками."""

    # --- события ------------------------------------------------------------
    def handle_event(self, event):
        """Возвращает строку-действие ('back', 'open_store', ...) или None."""
        if event.type == pygame.MOUSEMOTION:
            self.back_button.hovered = (
                self.back_button.visible
                and self.back_button.is_clicked(
                    (event.pos[0] - self.pos[0], event.pos[1] - self.pos[1])))
        elif (event.type == pygame.MOUSEBUTTONDOWN
                and self.back_button.visible
                and self.back_button.is_clicked(
                    (event.pos[0] - self.pos[0], event.pos[1] - self.pos[1]))):
            return 'back'
        return self.handle_content_event(event)

    def handle_content_event(self, event):
        return None


class ButtonOverlay(OverlayWindow):
    """Вертикальное меню из кнопок. Опционально — цена энергии и цены тестов."""

    def __init__(self, button_list, avatar, energy_cost=0, test_costs=None):
        super().__init__()
        self.avatar = avatar
        self.energy_cost = energy_cost
        self.test_costs = test_costs
        self.buttons = [
            Button((self.width - 240) // 2, 10 + i * 70, 240, 50, text, action)
            for i, (text, action) in enumerate(button_list)
        ]

    def draw_content(self, screen):
        if self.energy_cost > 0:
            label = font.render(
                f"Каждый урок отнимает по {self.energy_cost} энергии. "
                f"За каждые {LESSONS_PER_STIPEND} уроков — стипендия {STIPEND_AMOUNT} руб.", True, WHITE)
            screen.blit(label, label.get_rect(
                center=(self.pos[0] + self.width // 2,
                        self.pos[1] + self.height - 100)))
        for i, button in enumerate(self.buttons):
            button.draw(screen, self.pos)
            if self.test_costs and i < len(self.test_costs):
                test_num = i + 1
                if test_num not in self.avatar.purchased_tests:
                    cost = font.render(f"{self.test_costs[i]} рублей",
                                       True, WHITE)
                    screen.blit(cost, cost.get_rect(
                        center=(self.pos[0] + self.width // 2,
                                self.pos[1] + 5 + i * 70)))

    def handle_content_event(self, event):
        for i, button in enumerate(self.buttons):
            if event.type == pygame.MOUSEMOTION:
                button.hovered = button.rect.move(self.pos).collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and \
                    button.rect.move(self.pos).collidepoint(event.pos):
                if self.test_costs and i < len(self.test_costs):
                    return self._handle_test_click(i, button.action)
                return self._handle_lesson_click(button.action)
        return None

    def _handle_test_click(self, i, action):
        """Покупка теста (если ещё не куплен) и переход к нему."""
        test_num = i + 1
        if test_num in self.avatar.purchased_tests:
            return action
        cost = self.test_costs[i]
        if self.avatar.rouns >= cost:
            self.avatar.rouns -= cost
            self.avatar.purchased_tests.append(test_num)
            self.avatar.save_to_db()
            return action
        return None

    def _handle_lesson_click(self, action):
        """Списание энергии за урок и переход к теме."""
        if self.energy_cost == 0 or self.avatar.energy >= self.energy_cost:
            if self.energy_cost > 0:
                self.avatar.energy = max(0, self.avatar.energy - self.energy_cost)
                self.avatar.save_to_db()
            return action
        return None


class TextOverlay(OverlayWindow):
    """Прочтение темы: прокручиваемый текст, награда за прочтение."""

    def __init__(self, text, avatar):
        super().__init__(back_text="Понятно")
        self.avatar = avatar
        self.line_height = 30
        self.text_area_height = self.height - 100
        self.lines = wrap_text(text, font, self.width - 2 * self.margin)
        self.total_text_height = len(self.lines) * self.line_height
        self.scroll_offset = 0

    def draw_content(self, screen):
        text_pos_y = self.pos[1] + 50
        start = max(0, self.scroll_offset // self.line_height)
        end = min(len(self.lines),
                  start + self.text_area_height // self.line_height + 1)
        for i in range(start, end):
            line = font.render(self.lines[i], True, WHITE)
            screen.blit(line, (self.pos[0] + self.margin,
                               text_pos_y + i * self.line_height - self.scroll_offset))

    def handle_event(self, event):
        # «Понятно» = прочитал тему → награда
        if event.type == pygame.MOUSEBUTTONDOWN and \
                self.back_button.rect.move(self.pos).collidepoint(event.pos):
            # Увеличиваем счётчик уроков
            self.avatar.lessons_count += 1
            # Проверяем, не набралось ли 5 уроков
            if self.avatar.lessons_count % LESSONS_PER_STIPEND == 0:
                self.avatar.rouns += STIPEND_AMOUNT
            self.avatar.save_to_db()
            return 'back'
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * 30
            self.scroll_offset = max(0, min(
                self.scroll_offset,
                max(0, self.total_text_height - self.text_area_height)))
        return None


def _shuffle_options(question):
    """Перемешивает варианты ответов и пересчитывает индекс верного.

    Работает с копией, чтобы не менять глобальный банк вопросов —
    иначе порядок «замёрз» бы после первого теста.
    """
    q = dict(question)
    order = list(range(len(q["options"])))
    random.shuffle(order)
    q["options"] = [q["options"][i] for i in order]
    q["correct"] = order.index(q["correct"])
    return q


class TestOverlay(OverlayWindow):
    """Тест: QUESTIONS_PER_TEST случайных вопросов, варианты перемешаны,
    награда за 10/10."""

    def __init__(self, test_num, avatar):
        super().__init__()
        self.avatar = avatar
        self.test_num = test_num
        self.questions = [_shuffle_options(q)
                          for q in random.sample(QUESTIONS, QUESTIONS_PER_TEST)]
        self.current_question = 0
        self.correct_answers = 0
        self.selected_option = None
        self.option_buttons = []
        self.reward_granted = 0
        self.next_button = Button(self.width - 110, self.height - 60, 100, 50,
                                  "Вперед", color=PEACH_COLOR)

    # --- логика -------------------------------------------------------------
    def check_answer(self, option_idx):
        if self.selected_option is not None:
            return
        correct_idx = self.questions[self.current_question]["correct"]
        if option_idx == correct_idx:
            self.correct_answers += 1
        else:
            self.option_buttons[option_idx].color = RED
        self.option_buttons[correct_idx].color = LIGHT_GREEN
        self.selected_option = option_idx

    def next_question(self):
        if self.selected_option is None:
            return
        self.current_question += 1
        self.selected_option = None
        self.option_buttons = []
        if self.current_question == QUESTIONS_PER_TEST:
            self._grant_reward()

    def _grant_reward(self):
        """Награда выдаётся один раз, только за идеальный результат."""
        if self.correct_answers == QUESTIONS_PER_TEST and \
                self.test_num not in self.avatar.completed_tests:
            self.reward_granted = TEST_REWARDS[self.test_num]
            self.avatar.rouns += self.reward_granted
            self.avatar.completed_tests.append(self.test_num)
            self.avatar.passed_tests += 1
            self.avatar.update_status()
            self.avatar.save_to_db()

    # --- отрисовка ------------------------------------------------------------
    def draw_content(self, screen):
        if self.current_question < QUESTIONS_PER_TEST:
            self._draw_question(screen)
        else:
            self._draw_result(screen)

    def _draw_question(self, screen):
        question = font.render(
            self.questions[self.current_question]["question"], True, WHITE)
        screen.blit(question, (self.pos[0] + self.margin, self.pos[1] + 50))
        if not self.option_buttons:
            for i, option in enumerate(self.questions[self.current_question]["options"]):
                self.option_buttons.append(Button(
                    self.pos[0] + self.margin, self.pos[1] + 100 + i * 60,
                    self.width - 2 * self.margin, 50, option,
                    action=lambda i=i: self.check_answer(i),
                    color=PEACH_COLOR))
        for btn in self.option_buttons:
            btn.draw(screen)
        if self.selected_option is not None:
            self.next_button.draw(screen, self.pos)

    def _draw_result(self, screen):
        result = result_font.render(
            f"{self.correct_answers} из {QUESTIONS_PER_TEST}", True, WHITE)
        screen.blit(result, result.get_rect(
            center=(self.pos[0] + self.width // 2, self.pos[1] + self.height // 2)))
        if self.reward_granted:
            reward = result_font.render(f"+{self.reward_granted} рублей",
                                        True, WHITE)
            screen.blit(reward, reward.get_rect(
                center=(self.pos[0] + self.width // 2,
                        self.pos[1] + self.height // 2 + result.get_height() + 10)))

    # --- события ----------------------------------------------------------------
    def handle_content_event(self, event):
        if self.current_question >= QUESTIONS_PER_TEST:
            return None
        for btn in self.option_buttons:
            if event.type == pygame.MOUSEMOTION:
                btn.hovered = btn.rect.collidepoint(event.pos)
            elif (event.type == pygame.MOUSEBUTTONDOWN
                    and btn.rect.collidepoint(event.pos)
                    and self.selected_option is None):
                btn.action()
        if self.selected_option is not None:
            if event.type == pygame.MOUSEMOTION:
                self.next_button.hovered = self.next_button.rect.move(
                    self.pos).collidepoint(event.pos)
            elif (event.type == pygame.MOUSEBUTTONDOWN
                    and self.next_button.rect.move(self.pos).collidepoint(event.pos)):
                self.next_question()
        return None


class PhoneOverlay(OverlayWindow):
    """Экран телефона с ярлыком магазина."""

    WIDTH, HEIGHT = 467, 700

    def __init__(self, avatar):
        super().__init__(width=self.WIDTH, height=self.HEIGHT)
        self.avatar = avatar
        self.phone_image = self._load_image('phone_screen.png', (self.width, self.height))
        self.cart_icon = self._load_image('cart_icon.png', (150, 150))
        self.cart_rect = pygame.Rect(100, self.height // 4 - 75, 150, 150)

    @staticmethod
    def _load_image(name, size):
        try:
            image = pygame.image.load(os.path.join(ASSETS_DIR, name))
            return pygame.transform.scale(image, size)
        except pygame.error:
            return None

    def draw_content(self, screen):
        if self.phone_image:
            screen.blit(self.phone_image, self.pos)
        if self.cart_icon:
            screen.blit(self.cart_icon,
                        (self.pos[0] + self.cart_rect.x, self.pos[1] + self.cart_rect.y))
            label = font.render("Магазин", True, BLACK)
            screen.blit(label, label.get_rect(
                center=(self.pos[0] + self.cart_rect.centerx,
                        self.pos[1] + self.cart_rect.bottom + 15)))

    def handle_content_event(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN
                and self.cart_rect.move(self.pos).collidepoint(event.pos)):
            return 'open_store'
        return None


class StoreOverlay(OverlayWindow):
    """Магазин: список предметов пола игрока, покупка добавляет в инвентарь."""

    WIDTH, HEIGHT = 467, 700
    CONTENT_HEIGHT = 500
    ITEM_HEIGHT = 280
    ITEM_SIZE = 160

    def __init__(self, avatar):
        super().__init__(width=self.WIDTH, height=self.HEIGHT)
        self.avatar = avatar
        self.scroll_offset = 0
        self.selected_item = None
        self.buy_button = Button(self.width // 2 - 100, self.height - 170,
                                 200, 50, "Купить")
        self.buy_button.visible = False
        self.phone_image = PhoneOverlay._load_image('phone_screen.png',
                                                    (self.width, self.height))
        self.refresh_items()

    def refresh_items(self):
        """Пересобирает список товаров: уже купленные не показываем."""
        unlocked = set(self.avatar.unlocked_hair) | set(self.avatar.unlocked_clothes)
        self.items = [item for item in PURCHASABLE_ITEMS
                      if item["gender"] == self.avatar.gender
                      and item["name"] not in unlocked]
        self.item_rects = []

        left = (self.WIDTH - self.ITEM_SIZE) // 2

        for i, item in enumerate(self.items):
            image = PhoneOverlay._load_image(item["image"],
                                             (self.ITEM_SIZE, self.ITEM_SIZE))
            rect = pygame.Rect(left, 100 + i * self.ITEM_HEIGHT,
                               self.ITEM_SIZE, self.ITEM_SIZE)
            self.item_rects.append((rect, item, image))

    def draw_content(self, screen):
        if self.phone_image:
            screen.blit(self.phone_image, self.pos)
        small_font = pygame.font.Font(None, 24)

        for rect, item, image in self.item_rects:
            adjusted = rect.move(0, -self.scroll_offset)
            absolute = adjusted.move(*self.pos)

            if not (adjusted.bottom > 20 and adjusted.top < self.CONTENT_HEIGHT):
                continue

            pygame.draw.rect(screen, WHITE, absolute, border_radius=10)
            pygame.draw.rect(screen, BLACK, absolute, 2, border_radius=10)

            if image:
                image_rect = image.get_rect(center=(absolute.centerx, absolute.top + 60))
                screen.blit(image, image_rect.topleft)

            # Рисуем название с подложкой
            display_name = ITEM_DISPLAY_NAMES.get(item["name"], item["name"])
            name = small_font.render(display_name, True, WHITE)
            name_rect = name.get_rect(center=(absolute.centerx, absolute.top + 110))

            # Подложка под текст
            padding = 4
            bg_rect = name_rect.inflate(padding * 2, padding * 2)
            bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))  # полупрозрачный чёрный
            screen.blit(bg_surface, bg_rect.topleft)

            screen.blit(name, name_rect)

            # Рисуем цену с подложкой
            price = small_font.render(f"{item['price']} руб.", True, WHITE)
            price_rect = price.get_rect(center=(absolute.centerx, absolute.bottom - 30))

            # Подложка под цену
            bg_rect2 = price_rect.inflate(padding * 2, padding * 2)
            bg_surface2 = pygame.Surface(bg_rect2.size, pygame.SRCALPHA)
            bg_surface2.fill((0, 0, 0, 180))
            screen.blit(bg_surface2, bg_rect2.topleft)

            screen.blit(price, price_rect)

            if self.selected_item is item:
                pygame.draw.rect(screen, BUTTON_COLOR, absolute, 3, border_radius=10)

        self.buy_button.draw(screen, self.pos)

    def handle_content_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            for rect, item, _ in self.item_rects:
                if rect.move(0, -self.scroll_offset).move(*self.pos).collidepoint(event.pos):
                    self.selected_item = item
                    self.buy_button.visible = True
                    return None
            if self.buy_button.visible and \
                    self.buy_button.rect.move(self.pos).collidepoint(event.pos):
                return self.buy_item()
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * 30
            max_scroll = max(0, len(self.item_rects) * self.ITEM_HEIGHT - self.CONTENT_HEIGHT)
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
        return None

    def buy_item(self):
        """Покупает выбранный предмет, если хватает рублей."""
        item = self.selected_item
        if item is None or self.avatar.rouns < item["price"]:
            return None
        self.avatar.rouns -= item["price"]
        target = (self.avatar.unlocked_hair if item["type"] == "hair"
                  else self.avatar.unlocked_clothes)
        if item["name"] not in target:
            target.append(item["name"])
        self.avatar.save_to_db()
        self.avatar.load_images()
        self.selected_item = None
        self.buy_button.visible = False
        self.refresh_items()
        return None


class ConfirmResetOverlay(OverlayWindow):
    """Модальное подтверждение сброса прогресса."""

    def __init__(self):
        super().__init__(width=400, height=200)
        self.message = "Весь прогресс игры будет потерян. Вы уверены?"
        self.yes_button = Button(self.width // 4 - 60, self.height - 60, 120, 50,
                                 "Да", action="confirm_reset", color=RED)
        self.no_button = Button(3 * self.width // 4 - 60, self.height - 60, 120, 50,
                                "Нет", action="cancel", color=LIGHT_GREEN)
        self.back_button.visible = False

    def draw_content(self, screen):
        for i, line in enumerate(wrap_text(self.message, confirm_font,
                                           self.width - 40)):
            surface = confirm_font.render(line, True, WHITE)
            screen.blit(surface, surface.get_rect(
                center=(self.pos[0] + self.width // 2, self.pos[1] + 50 + i * 30)))
        self.yes_button.draw(screen, self.pos)
        self.no_button.draw(screen, self.pos)

    def handle_content_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.yes_button.hovered = self.yes_button.rect.move(self.pos).collidepoint(event.pos)
            self.no_button.hovered = self.no_button.rect.move(self.pos).collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.yes_button.rect.move(self.pos).collidepoint(event.pos):
                return "confirm_reset"
            if self.no_button.rect.move(self.pos).collidepoint(event.pos):
                return "cancel"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                return "confirm_reset"
            if event.key == pygame.K_ESCAPE:
                return "cancel"
        return None


class HelpOverlay(OverlayWindow):
    """Окно с правилами игры, без награды за прочтение."""

    def __init__(self, text):
        super().__init__(back_text="Назад")
        self.line_height = 30
        self.text_area_height = self.height - 100
        self.lines = wrap_text(text, font, self.width - 2 * self.margin)
        self.total_text_height = len(self.lines) * self.line_height
        self.scroll_offset = 0

    def draw_content(self, screen):
        text_pos_y = self.pos[1] + 50
        start = max(0, self.scroll_offset // self.line_height)
        end = min(len(self.lines),
                  start + self.text_area_height // self.line_height + 1)
        for i in range(start, end):
            line = font.render(self.lines[i], True, WHITE)
            screen.blit(line, (self.pos[0] + self.margin,
                               text_pos_y + i * self.line_height - self.scroll_offset))

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * 30
            self.scroll_offset = max(0, min(
                self.scroll_offset,
                max(0, self.total_text_height - self.text_area_height)))
        return super().handle_event(event)

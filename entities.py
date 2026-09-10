"""Игровые сущности: аватар игрока и редакторы внешности.

Avatar — модель игрока: состояние, загрузка/сохранение через db.py,
выводимый статус (не хранится в БД, вычисляется из passed_tests).
AvatarCreator — экран создания персонажа (пол, внешность, никнейм).
Inventory — экран выбора внешности из разблокированных предметов.
"""

import os
import pygame

import db
from constants import (
    ASSETS_DIR, SCREEN_WIDTH, SCREEN_HEIGHT,
    LIGHT_GREEN, STATUSES, MAX_ENERGY, START_ROUNS,
)
from ui import Button


class Avatar:
    """Состояние игрока и его персонаж на экране."""

    def __init__(self):
        self.purchased_tests = []
        self.completed_tests = []
        self.nickname = ""
        self.load_from_db()

    # ------------------------------------------------------------- загрузка
    def load_from_db(self):
        state = db.load_player()
        if state is None:
            self._set_defaults()
            self.save_to_db()
        else:
            for key, value in state.items():
                setattr(self, key, value)
            self.lessons_count = state.get('lessons_count', 0)
            self.update_status()
        self._validate_appearance()
        self.load_images()

    def _set_defaults(self):
        self.gender = 'male'
        self.hair, self.clothes = 'male_hair1', 'male_clothes1'
        self.unlocked_hair, self.unlocked_clothes = db.default_unlocked_names(self.gender)
        self.rouns = START_ROUNS
        self.current_day = 1
        self.avatar_created = False
        self.energy = MAX_ENERGY
        self.passed_tests = 0
        self.status = STATUSES[0]
        self.purchased_tests = []
        self.completed_tests = []
        self.nickname = ""
        self.lessons_count = 0

    def _validate_appearance(self):
        """Надетый предмет обязан быть разблокирован — иначе дефолт."""
        if not self.unlocked_hair:
            self.unlocked_hair = db.default_unlocked_names(self.gender)[0]
        if not self.unlocked_clothes:
            self.unlocked_clothes = db.default_unlocked_names(self.gender)[1]
        if self.hair not in self.unlocked_hair:
            self.hair = self.unlocked_hair[0]
        if self.clothes not in self.unlocked_clothes:
            self.clothes = self.unlocked_clothes[0]

    def load_images(self):
        """Загружает PNG текущей внешности. Пропущенный файл — понятная ошибка."""
        try:
            self.hair_img = pygame.image.load(
                os.path.join(ASSETS_DIR, f'{self.hair}.png'))
            self.clothes_img = pygame.image.load(
                os.path.join(ASSETS_DIR, f'{self.clothes}.png'))
        except pygame.error as exc:
            raise FileNotFoundError(
                f"Не найден файл внешности персонажа: {exc}") from exc

    def draw(self, screen, position):
        screen.blit(self.clothes_img, position)
        screen.blit(self.hair_img, position)

    # ------------------------------------------------------------- сохранение
    def save_to_db(self):
        db.save_player({
            'nickname': self.nickname,
            'gender': self.gender,
            'hair': self.hair,
            'clothes': self.clothes,
            'rouns': int(self.rouns),
            'current_day': self.current_day,
            'avatar_created': self.avatar_created,
            'energy': self.energy,
            'passed_tests': self.passed_tests,
            'unlocked_hair': self.unlocked_hair,
            'unlocked_clothes': self.unlocked_clothes,
            'purchased_tests': self.purchased_tests,
            'completed_tests': self.completed_tests,
            'lessons_count': self.lessons_count,
        })

    def update_status(self):
        """Статус — выводимое поле: всегда функция от passed_tests."""
        self.status = STATUSES[min(self.passed_tests, len(STATUSES) - 1)]

    def reset(self):
        self._set_defaults()
        self.save_to_db()
        self.load_images()


class _AppearanceEditorBase:
    """Общая логика листания внешности для AvatarCreator и Inventory."""

    AVATAR_POS = (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 315)

    def get_current_selection(self):
        raise NotImplementedError

    def _load_part_images(self, parts):
        return {name: pygame.image.load(os.path.join(ASSETS_DIR, f'{name}.png'))
                for name in parts}

    def draw_avatar(self, screen, gender, selection):
        x, y = self.AVATAR_POS
        screen.blit(self.images[gender]['clothes'][selection['clothes']], (x, y))
        screen.blit(self.images[gender]['hair'][selection['hair']], (x, y))

    @staticmethod
    def _cycle(current, direction, length):
        return (current + (-1 if direction == 'prev' else 1)) % length if length else 0


class AvatarCreator(_AppearanceEditorBase):
    """Создание персонажа: пол, причёска, одежда, никнейм 3–15 символов."""

    def __init__(self, avatar):
        self.avatar = avatar
        self.genders = ['male', 'female']
        self.current = {'gender': self.genders.index(avatar.gender),
                        'hair': 0, 'clothes': 0}
        self.nickname_input = ""
        self.nickname_confirmed = False
        self.input_rect = pygame.Rect(100, 300, 200, 40)
        self.confirm_button = Button(320, 300, 40, 40, "ОК",
                                     color=LIGHT_GREEN)
        self.continue_button = Button(1100, 50, 150, 50, "Продолжить")
        self.images = {}
        self.set_gender(avatar.gender)
        self._select_worn(avatar.hair, avatar.clothes)

    # --- данные -------------------------------------------------------------
    def set_gender(self, gender):
        self.current['gender'] = self.genders.index(gender)
        default_hair, default_clothes = db.default_unlocked_names(gender)
        self.options = {'hair': default_hair, 'clothes': default_clothes}
        # части загружаем для обоих полов — на случай переключения
        for gender_ in self.genders:
            hair_, clothes_ = db.default_unlocked_names(gender_)
            self.images[gender_] = {
                'hair': self._load_part_images(hair_),
                'clothes': self._load_part_images(clothes_),
            }
        self.current['hair'] = min(self.current.get('hair', 0),
                                   len(self.options['hair']) - 1)
        self.current['clothes'] = min(self.current.get('clothes', 0),
                                      len(self.options['clothes']) - 1)

    def _select_worn(self, hair, clothes):
        if hair in self.options['hair']:
            self.current['hair'] = self.options['hair'].index(hair)
        if clothes in self.options['clothes']:
            self.current['clothes'] = self.options['clothes'].index(clothes)

    def get_current_selection(self):
        gender = self.genders[self.current['gender']]
        return {
            'gender': gender,
            'hair': self.options['hair'][self.current['hair']],
            'clothes': self.options['clothes'][self.current['clothes']],
        }

    def cycle(self, part, direction):
        if part == 'gender':
            new_gender = self.genders[self._cycle(self.current['gender'],
                                                  direction, 2)]
            self.set_gender(new_gender)
        else:
            self.current[part] = self._cycle(self.current[part], direction,
                                             len(self.options[part]))

    def confirm_nickname(self):
        if 3 <= len(self.nickname_input) <= 15:
            self.nickname_confirmed = True
            self.avatar.nickname = self.nickname_input

    def type_character(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.nickname_input = self.nickname_input[:-1]
        elif event.unicode and event.unicode.isprintable() \
                and len(self.nickname_input) < 15:
            self.nickname_input += event.unicode

    def can_continue(self):
        return self.nickname_confirmed

    def save(self):
        selection = self.get_current_selection()
        self.avatar.gender = selection['gender']
        self.avatar.hair = selection['hair']
        self.avatar.clothes = selection['clothes']
        self.avatar.unlocked_hair, self.avatar.unlocked_clothes = \
            db.default_unlocked_names(self.avatar.gender)
        self.avatar.avatar_created = True
        self.avatar.nickname = self.nickname_input
        self.avatar.save_to_db()
        self.avatar.load_images()


class Inventory(_AppearanceEditorBase):
    """Выбор внешности из уже разблокированных предметов."""

    def __init__(self, avatar):
        self.avatar = avatar
        self.options = {
            'hair': avatar.unlocked_hair or ['male_hair1'],
            'clothes': avatar.unlocked_clothes or ['male_clothes1'],
        }
        self.current = {
            'hair': self.options['hair'].index(avatar.hair)
                    if avatar.hair in self.options['hair'] else 0,
            'clothes': self.options['clothes'].index(avatar.clothes)
                       if avatar.clothes in self.options['clothes'] else 0,
        }
        self.images = {avatar.gender: {
            'hair': self._load_part_images(self.options['hair']),
            'clothes': self._load_part_images(self.options['clothes']),
        }}

    def get_current_selection(self):
        return {
            'hair': self.options['hair'][self.current['hair']],
            'clothes': self.options['clothes'][self.current['clothes']],
        }

    def cycle(self, part, direction):
        self.current[part] = self._cycle(self.current[part], direction,
                                         len(self.options[part]))

    def draw(self, screen):
        selection = self.get_current_selection()
        self.draw_avatar(screen, self.avatar.gender, selection)

    def save(self):
        selection = self.get_current_selection()
        self.avatar.hair = selection['hair']
        self.avatar.clothes = selection['clothes']
        self.avatar.save_to_db()
        self.avatar.load_images()

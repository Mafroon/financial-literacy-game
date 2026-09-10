"""Нормализованный слой доступа к данным сохранения игры.

Схема (до 3NF):
    players        — одна строка на сохранение, только скалярные атрибуты
    items          — каталог предметов (справочник)
    tests          — каталог тестов (справочник)
    player_items   — M:N «игрок <-> разблокированные предметы»
    player_tests   — M:N «игрок <-> тесты» (флаги purchased / completed)

Принципы:
    * списки НЕ хранятся строками в колонках (1NF), никакого eval()
    * статус НЕ хранится — он выводимый, зависит только от passed_tests
    * внешние ключи + транзакции + каскадное удаление
    * каталоги (ITEM_CATALOG, TEST_CATALOG) — ЕДИНСТВЕННЫЙ источник правды:
      PURCHASABLE_ITEMS, TEST_COSTS, TEST_REWARDS в constants.py
      вычисляются из них, дублей нет
"""

import os
import sqlite3
import sys
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _default_db_path():
    """game.db живёт рядом со скриптом; в собранном .exe — рядом с exe-шником,
    иначе PyInstaller распаковывал бы его во временную папку и сейв терялся бы."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'game.db')
    return os.path.join(BASE_DIR, 'game.db')


DB_PATH = _default_db_path()

# Каталог предметов: (name, type, gender, price, image, is_default) — ЕДИНСТВЕННЫЙ источник
ITEM_CATALOG = [
    ('male_hair1', 'hair', 'male', 0, 'male_hair1.png', 1),
    ('male_hair2', 'hair', 'male', 0, 'male_hair2.png', 1),
    ('male_hair3', 'hair', 'male', 5000, 'male_hair3_icon.png', 0),
    ('male_clothes1', 'clothes', 'male', 0, 'male_clothes1.png', 1),
    ('male_clothes2', 'clothes', 'male', 0, 'male_clothes2.png', 1),
    ('male_clothes3', 'clothes', 'male', 0, 'male_clothes3.png', 1),
    ('male_clothes4', 'clothes', 'male', 8500, 'male_clothes4_icon.png', 0),
    ('female_hair1', 'hair', 'female', 0, 'female_hair1.png', 1),
    ('female_hair2', 'hair', 'female', 0, 'female_hair2.png', 1),
    ('female_hair3', 'hair', 'female', 5000, 'female_hair3_icon.png', 0),
    ('female_clothes1', 'clothes', 'female', 0, 'female_clothes1.png', 1),
    ('female_clothes2', 'clothes', 'female', 0, 'female_clothes2.png', 1),
    ('female_clothes3', 'clothes', 'female', 0, 'female_clothes3.png', 1),
    ('female_clothes4', 'clothes', 'female', 8500, 'female_clothes4_icon.png', 0),
]

# Каталог тестов: (id, title, cost, reward) — ЕДИНСТВЕННЫЙ источник
TEST_CATALOG = [
    (1, 'Эконом', 0, 500),
    (2, 'Накопитель', 3200, 1000),
    (3, 'Инвестор', 8500, 1500),
    (4, 'Стратег', 13000, 2000),
    (5, 'Эксперт', 22000, 2500),
    (6, 'Магнат', 30000, 3000),
    (7, 'Мудрец', 50000, 3500),
]


# ---------------------------------------------------------------- соединение

@contextmanager
def db():
    """Контекстный менеджер: PRAGMA foreign_keys, автокоммит/откат."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------- схема

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    type          TEXT NOT NULL CHECK (type IN ('hair', 'clothes')),
    gender        TEXT NOT NULL CHECK (gender IN ('male', 'female')),
    price         INTEGER NOT NULL DEFAULT 0 CHECK (price >= 0),
    image         TEXT NOT NULL,
    is_default    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tests (
    id      INTEGER PRIMARY KEY,
    title   TEXT NOT NULL,
    cost    INTEGER NOT NULL DEFAULT 0 CHECK (cost >= 0),
    reward  INTEGER NOT NULL DEFAULT 0 CHECK (reward >= 0)
);

CREATE TABLE IF NOT EXISTS players (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    nickname        TEXT NOT NULL DEFAULT '' CHECK (length(nickname) <= 15),
    gender          TEXT NOT NULL CHECK (gender IN ('male', 'female')),
    hair_id         INTEGER NOT NULL REFERENCES items(id),
    clothes_id      INTEGER NOT NULL REFERENCES items(id),
    rouns           INTEGER NOT NULL DEFAULT 500,  -- синхронизировано с START_ROUNS в constants.py
    current_day     INTEGER NOT NULL DEFAULT 1 CHECK (current_day >= 1),
    avatar_created  INTEGER NOT NULL DEFAULT 0,
    energy          INTEGER NOT NULL DEFAULT 5 CHECK (energy BETWEEN 0 AND 5),
    passed_tests    INTEGER NOT NULL DEFAULT 0 CHECK (passed_tests BETWEEN 0 AND 7),
    lessons_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_items (
    player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    item_id     INTEGER NOT NULL REFERENCES items(id),
    PRIMARY KEY (player_id, item_id)
);

CREATE TABLE IF NOT EXISTS player_tests (
    player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    test_id     INTEGER NOT NULL REFERENCES tests(id),
    purchased   INTEGER NOT NULL DEFAULT 0,
    completed   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, test_id)
);

CREATE INDEX IF NOT EXISTS idx_player_items ON player_items(player_id);
CREATE INDEX IF NOT EXISTS idx_player_tests ON player_tests(player_id);
"""


def _create_schema(conn):
    conn.executescript(_SCHEMA)


def _seed_catalogs(conn):
    conn.executemany(
        'INSERT OR IGNORE INTO items (name, type, gender, price, image, is_default)'
        ' VALUES (?, ?, ?, ?, ?, ?)', ITEM_CATALOG)
    conn.executemany(
        'INSERT OR IGNORE INTO tests (id, title, cost, reward) VALUES (?, ?, ?, ?)',
        TEST_CATALOG)


# -------------------------------------------------------------- публичное API

def init_database():
    """Создаёт/обновляет схему"""
    with db() as conn:
        _create_schema(conn)
        _seed_catalogs(conn)


def _default_names(gender):
    hair = [n for n, t, g, *rest in ITEM_CATALOG
            if t == 'hair' and g == gender and rest[2] == 1]
    clothes = [n for n, t, g, *rest in ITEM_CATALOG
               if t == 'clothes' and g == gender and rest[2] == 1]
    return hair, clothes


def default_unlocked_names(gender):
    return _default_names(gender)


def load_player():
    """Загружает сохранение. Возвращает dict или None, если сохранения нет."""
    with db() as conn:
        row = conn.execute(
            'SELECT p.*, hi.name AS hair, ci.name AS clothes FROM players p '
            'JOIN items hi ON hi.id = p.hair_id '
            'JOIN items ci ON ci.id = p.clothes_id WHERE p.id = 1'
        ).fetchone()
        if row is None:
            return None

        items = conn.execute(
            'SELECT i.name, i.type FROM player_items pi '
            'JOIN items i ON i.id = pi.item_id WHERE pi.player_id = 1'
        ).fetchall()
        tests = conn.execute(
            'SELECT test_id, purchased, completed FROM player_tests '
            'WHERE player_id = 1'
        ).fetchall()

        state = dict(row)
        state.pop('hair_id', None)
        state.pop('clothes_id', None)
        state['avatar_created'] = bool(state['avatar_created'])
        state['lessons_count'] = state.get('lessons_count', 0)
        state['unlocked_hair'] = [r['name'] for r in items if r['type'] == 'hair']
        state['unlocked_clothes'] = [r['name'] for r in items if r['type'] == 'clothes']
        state['purchased_tests'] = [r['test_id'] for r in tests if r['purchased']]
        state['completed_tests'] = [r['test_id'] for r in tests if r['completed']]
        return state


def _save_player(conn, state):
    """Upsert игрока + полная перезапись связанных таблиц. Одна транзакция."""
    conn.execute(
        """INSERT INTO players
               (id, nickname, gender, hair_id, clothes_id, rouns,
                current_day, avatar_created, energy, passed_tests, lessons_count)
           VALUES (1, :nickname, :gender,
                   (SELECT id FROM items WHERE name = :hair),
                   (SELECT id FROM items WHERE name = :clothes),
                   :rouns, :current_day, :avatar_created, :energy, :passed_tests, :lessons_count)
           ON CONFLICT(id) DO UPDATE SET
               nickname       = excluded.nickname,
               gender         = excluded.gender,
               hair_id        = excluded.hair_id,
               clothes_id     = excluded.clothes_id,
               rouns          = excluded.rouns,
               current_day    = excluded.current_day,
               avatar_created = excluded.avatar_created,
               energy         = excluded.energy,
               passed_tests   = excluded.passed_tests,
               lessons_count  = excluded.lessons_count""",
        {**state,
         'rouns': int(state['rouns']),
         'avatar_created': int(bool(state['avatar_created']))})

    unlocked = list(state['unlocked_hair']) + list(state['unlocked_clothes'])
    conn.execute('DELETE FROM player_items WHERE player_id = 1')
    conn.executemany(
        'INSERT OR IGNORE INTO player_items (player_id, item_id)'
        ' VALUES (1, (SELECT id FROM items WHERE name = ?))',
        [(n,) for n in unlocked])

    test_ids = set(state['purchased_tests']) | set(state['completed_tests'])
    conn.execute('DELETE FROM player_tests WHERE player_id = 1')
    if test_ids:
        conn.executemany(
            'INSERT OR IGNORE INTO player_tests (player_id, test_id, purchased, completed)'
            ' VALUES (1, ?, ?, ?)',
            [(tid, int(tid in state['purchased_tests']),
              int(tid in state['completed_tests'])) for tid in sorted(test_ids)])


def save_player(state):
    """Сохраняет полное состояние игрока атомарно."""
    with db() as conn:
        _save_player(conn, state)


def reset_save():
    """Удаляет сохранение; связи удалятся каскадом."""
    with db() as conn:
        conn.execute('DELETE FROM players WHERE id = 1')

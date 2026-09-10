"""Финансовая Грамотность — точка входа.

Запуск:  python main.py
Требует: pygame
"""

import asyncio
import platform

import pygame

import db
import screens


async def main():
    try:
        db.init_database()
        screens.main_menu()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"Произошла ошибка: {exc}")
    finally:
        pygame.quit()


if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())

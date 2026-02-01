import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт конфигурации (проверяем переменные окружения)
try:
    from config import BOT_TOKEN, REVIEW_CHANNEL_ID, ADMIN_IDS, CASES
except ImportError:
    # Если config.py не существует, используем переменные окружения
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    REVIEW_CHANNEL_ID = os.getenv("REVIEW_CHANNEL_ID")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    CASES = {}  # Кейсы нужно будет загрузить по-другому

# Импортируем роутеры
from handlers.start import router as start_router
from handlers.cases import router as cases_router
from handlers.payment import router as payment_router
from handlers.inventory import router as inventory_router
from handlers.profile import router as profile_router
from handlers.admin import router as admin_router
from handlers.promo import router as promo_router
from handlers.reviews import router as reviews_router
from handlers.commands import router as commands_router

# Инициализируем БД
from database.db import Database

db = Database()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Для Render важно выводить логи в stdout
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    # Проверяем обязательные переменные
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        logger.error("Установите переменную окружения BOT_TOKEN или добавьте её в config.py")
        sys.exit(1)

    logger.info("⚔ SharpDrop Бот запускается...")
    logger.info(f"✅ Режим: {'PRODUCTION' if os.getenv('RENDER') else 'DEVELOPMENT'}")

    # Создаем бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Инициализируем диспетчер
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем все роутеры в правильном порядке
    routers = [
        commands_router,
        start_router,
        cases_router,
        payment_router,
        inventory_router,
        profile_router,
        admin_router,
        promo_router,
        reviews_router
    ]

    for router in routers:
        dp.include_router(router)

    # Проверяем подключение к БД
    try:
        test_user = db.get_user(1)  # Просто тестируем подключение
        logger.info("✅ База данных подключена")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")

    # Запускаем бота
    logger.info("🤖 Бот запущен и готов к работе!")

    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await bot.session.close()
        logger.info("👋 Бот завершил работу")


if __name__ == "__main__":
    # Для Windows: убираем kill_other_instances для продакшена
    if sys.platform == "win32" and not os.getenv("RENDER"):
        try:
            import subprocess

            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/NH'],
                capture_output=True,
                text=True
            )
            lines = [line for line in result.stdout.split('\n') if 'python.exe' in line]
            if len(lines) > 1:
                logger.warning(f"⚠️ Найдено {len(lines)} процессов Python")
        except:
            pass

    # Запускаем бота
    asyncio.run(main())
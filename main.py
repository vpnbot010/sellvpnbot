import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Health Check сервер
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Отключаем логи

def start_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 Health server started on port {port}")
    server.serve_forever()

# Запускаем health server в отдельном потоке
health_thread = threading.Thread(target=start_health_server, daemon=True)
health_thread.start()

# Telegram бот
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("✅ Бот работает на Render!")

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("🤖 Telegram бот запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

import subprocess
import sys


def install_requirements():
    """Устанавливаем зависимости"""
    requirements = [
        "aiogram==3.0.0",
        "sqlalchemy==2.0.0",
        "python-dotenv==1.0.0",
        "aiofiles==23.2.0"
    ]

    print("📦 Установка зависимостей...")

    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} установлен")
        except subprocess.CalledProcessError:
            print(f"❌ Ошибка установки {package}")

    print("\n✅ Все зависимости установлены!")
    print("\n📝 Создайте файл .env с настройками:")
    print("""
BOT_TOKEN=ваш_токен_бота
ADMIN_IDS=ваш_id_telegram
CARD_NUMBER=0000 0000 0000 0000
CARD_HOLDER=Иван Иванов
BANK=Тинькофф
REVIEW_CHANNEL_ID=@ваш_канал
    """)
    print("\n🚀 Запустите бота: python main.py")


if __name__ == "__main__":
    install_requirements()
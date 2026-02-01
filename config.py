import os
import json
from typing import List, Dict, Any

# Загружаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "8538291174:AAGpSIYxAG1YTLgpdXX5HGYy_6NXE9X0pQU")


# Обработка ADMIN_IDS
def parse_admin_ids() -> List[int]:
    """Парсим ID администраторов из переменной окружения"""
    admin_ids_str = os.getenv("ADMIN_IDS", "7025174146,6289277359")

    if not admin_ids_str:
        return [7025174146, 6289277359]  # Значение по умолчанию

    admin_ids = []
    for admin_id in admin_ids_str.split(","):
        admin_id = admin_id.strip()
        if admin_id:
            try:
                admin_ids.append(int(admin_id))
            except ValueError:
                print(f"⚠️ Предупреждение: '{admin_id}' не является числовым ID администратора")

    # Если список пустой, используем значение по умолчанию
    if not admin_ids:
        admin_ids = [7025174146, 6289277359]

    return admin_ids


ADMIN_IDS = parse_admin_ids()

# Настройки оплаты
CARD_NUMBER = os.getenv("CARD_NUMBER", "2200701240653037")
CARD_HOLDER = os.getenv("CARD_HOLDER", "Коптенко Е.В")
BANK = os.getenv("BANK", "Т-БАНК")

# Настройки вывода
MIN_WITHDRAWAL = 20.0
WITHDRAWAL_FEE = 0.0  # Комиссию берем на себя (0%)

# Настройки для Telegram Stars
STARS_TO_RUB = 1.67  # 1 звезда = 1.67 рубля (примерно)
MIN_STARS_PURCHASE = 10  # Минимальная покупка звездами

# Канал для отзывов
REVIEW_CHANNEL_ID = os.getenv("REVIEW_CHANNEL_ID", "@otzovikco2")


# Можно вынести кейсы в отдельный файл или переменную окружения для гибкости
def load_cases() -> Dict[int, Dict[str, Any]]:
    """Загружаем кейсы. В будущем можно вынести в JSON или базу данных."""
    return {
        1: {
            "name": "🟫 Кейс «Новичок»",
            "price": 19,  # рублей
            "stars": 10,  # звезд
            "price_gold": 10,  # GOLD за кейс
            "items": [
                {"name": "Glock «Sand»", "rarity": "Common", "chance": 65, "price": 0.07, "emoji": "⚪"},
                {"name": "USP «Line»", "rarity": "Common", "chance": 22, "price": 0.10, "emoji": "⚪"},
                {"name": "P350 «Forest»", "rarity": "Uncommon", "chance": 10, "price": 0.25, "emoji": "🔵"},
                {"name": "MP7 «Urban»", "rarity": "Rare", "chance": 2.8, "price": 1.50, "emoji": "🔷"},
                {"name": "Fabm «Boom»", "rarity": "Legendary", "chance": 0.2, "price": 150, "emoji": "🟣"}
            ]
        },
        2: {
            "name": "🟦 Кейс «Городской Штурм»",
            "price": 45,
            "stars": 26,
            "price_gold": 25,
            "items": [
                {"name": "Glock «Night»", "rarity": "Common", "chance": 55, "price": 0.12, "emoji": "⚪"},
                {"name": "MP5 «Urban»", "rarity": "Uncommon", "chance": 25, "price": 0.30, "emoji": "🔵"},
                {"name": "AKR «Carbon»", "rarity": "Rare", "chance": 15, "price": 1.80, "emoji": "🔷"},
                {"name": "FAMAS «Beagle»", "rarity": "Epic", "chance": 4.7, "price": 15, "emoji": "🟣"},
                {"name": "M4A1 «Lizard»", "rarity": "Legendary", "chance": 0.3, "price": 70, "emoji": "🟣"}
            ]
        },
        3: {
            "name": "🟨 Кейс «Зона Напряжения»",
            "price": 85,
            "stars": 50,
            "price_gold": 50,
            "items": [
                {"name": "USP «Stone»", "rarity": "Common", "chance": 48, "price": 0.20, "emoji": "⚪"},
                {"name": "UMP45 «Urban»", "rarity": "Uncommon", "chance": 27, "price": 0.40, "emoji": "🔵"},
                {"name": "M4 «Urban»", "rarity": "Rare", "chance": 18, "price": 2.0, "emoji": "🔷"},
                {"name": "FAMAS «Fury»", "rarity": "Epic", "chance": 6.6, "price": 35, "emoji": "🟣"},
                {"name": "M4 «Necromancer»", "rarity": "Legendary", "chance": 0.4, "price": 100, "emoji": "🟣"}
            ]
        },
        4: {
            "name": "⬛ Кейс «Чёрный Рынок»",
            "price": 150,
            "stars": 89,
            "price_gold": 85,
            "items": [
                {"name": "Glock «Stone»", "rarity": "Common", "chance": 40, "price": 0.25, "emoji": "⚪"},
                {"name": "MP7 «Grey»", "rarity": "Uncommon", "chance": 28, "price": 0.50, "emoji": "🔵"},
                {"name": "AKR «Sandstorm»", "rarity": "Rare", "chance": 22, "price": 3.0, "emoji": "🔷"},
                {"name": "SM1014 «Blaster»", "rarity": "Epic", "chance": 8.0, "price": 45, "emoji": "🟣"},
                {"name": "AKR «Necromancer»", "rarity": "Legendary", "chance": 2.0, "price": 200, "emoji": "🟣"}
            ]
        },
        5: {
            "name": "🌙 Кейс «Полуночный Дозор»",
            "price": 250,
            "stars": 149,
            "price_gold": 140,
            "items": [
                {"name": "USP «Night»", "rarity": "Common", "chance": 35, "price": 0.30, "emoji": "⚪"},
                {"name": "MP5 «Night»", "rarity": "Uncommon", "chance": 30, "price": 0.60, "emoji": "🔵"},
                {"name": "M4 «Night Wolf»", "rarity": "Rare", "chance": 22, "price": 4.5, "emoji": "🔷"},
                {"name": "FAMAS «Hull»", "rarity": "Epic", "chance": 11.0, "price": 50, "emoji": "🟣"},
                {"name": "SM1014 «Necromancer»", "rarity": "Arcane", "chance": 2.0, "price": 500, "emoji": "🔴"}
            ]
        },
        6: {
            "name": "🕶 Кейс «Секретная Операция»",
            "price": 380,
            "stars": 227,
            "price_gold": 210,
            "items": [
                {"name": "MP7 «Thorn»", "rarity": "Uncommon", "chance": 35, "price": 1.0, "emoji": "🔵"},
                {"name": "AKR «Tiger»", "rarity": "Rare", "chance": 30, "price": 8.0, "emoji": "🔷"},
                {"name": "M4 «Demon»", "rarity": "Epic", "chance": 20, "price": 65, "emoji": "🟣"},
                {"name": "P350 «Neon»", "rarity": "Epic", "chance": 11.5, "price": 80, "emoji": "🟣"},
                {"name": "MAC10 «Argo»", "rarity": "Arcane", "chance": 3.5, "price": 600, "emoji": "🔴"}
            ]
        },
        7: {
            "name": "👑 Кейс «Элитный Отряд»",
            "price": 550,
            "stars": 329,
            "price_gold": 300,
            "items": [
                {"name": "MP5 «Blaze»", "rarity": "Uncommon", "chance": 30, "price": 1.5, "emoji": "🔵"},
                {"name": "AKR «Hunter»", "rarity": "Rare", "chance": 28, "price": 12, "emoji": "🔷"},
                {"name": "FAMAS «Anger»", "rarity": "Epic", "chance": 20, "price": 75, "emoji": "🟣"},
                {"name": "M16 «Winged»", "rarity": "Epic", "chance": 15.0, "price": 90, "emoji": "🟣"},
                {"name": "MP9 «Hydra»", "rarity": "Arcane", "chance": 7.0, "price": 700, "emoji": "🔴"}
            ]
        },
        8: {
            "name": "💥 Кейс «Зона Разрушения»",
            "price": 700,
            "stars": 419,
            "price_gold": 380,
            "items": [
                {"name": "M4 «Predator»", "rarity": "Rare", "chance": 35, "price": 15, "emoji": "🔷"},
                {"name": "AKR «Nano»", "rarity": "Epic", "chance": 25, "price": 85, "emoji": "🟣"},
                {"name": "AWM «Scratch»", "rarity": "Epic", "chance": 25, "price": 95, "emoji": "🟣"},
                {"name": "UMP45 «Beast»", "rarity": "Arcane", "chance": 12, "price": 700, "emoji": "🔴"},
                {"name": "Fabm «Thief»", "rarity": "Arcane", "chance": 3, "price": 800, "emoji": "🔴"}
            ]
        },
        9: {
            "name": "🏆 Кейс «Триумф»",
            "price": 850,
            "stars": 509,
            "price_gold": 460,
            "items": [
                {"name": "AKR «Emperor»", "rarity": "Epic", "chance": 40, "price": 100, "emoji": "🟣"},
                {"name": "M4 «Dragon»", "rarity": "Epic", "chance": 30, "price": 120, "emoji": "🟣"},
                {"name": "AWP «Gold»", "rarity": "Arcane", "chance": 20, "price": 800, "emoji": "🔴"},
                {"name": "USP «Royal»", "rarity": "Arcane", "chance": 8, "price": 900, "emoji": "🔴"},
                {"name": "Karambit «King»", "rarity": "Mythical", "chance": 2, "price": 1500, "emoji": "🟡"}
            ]
        },
        10: {
            "name": "🌟 Кейс «Абсолют»",
            "price": 999,
            "stars": 598,
            "price_gold": 540,
            "items": [
                {"name": "M4 «Godlike»", "rarity": "Arcane", "chance": 35, "price": 850, "emoji": "🔴"},
                {"name": "AKR «Infinity»", "rarity": "Arcane", "chance": 30, "price": 900, "emoji": "🔴"},
                {"name": "AWP «Cosmos»", "rarity": "Arcane", "chance": 20, "price": 1000, "emoji": "🔴"},
                {"name": "Butterfly «Divine»", "rarity": "Mythical", "chance": 10, "price": 1800, "emoji": "🟡"},
                {"name": "Karambit «Universe»", "rarity": "Mythical", "chance": 5, "price": 2500, "emoji": "🟡"}
            ]
        }
    }


CASES = load_cases()


# Функция для экспорта конфига в JSON (для отладки)
def export_to_json(filename: str = "config_backup.json"):
    """Экспортировать конфигурацию в JSON файл (для бекапа)"""
    config_data = {
        "admin_ids": ADMIN_IDS,
        "cases_count": len(CASES),
        "min_withdrawal": MIN_WITHDRAWAL,
        "stars_to_rub": STARS_TO_RUB,
        "review_channel": REVIEW_CHANNEL_ID
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Конфигурация экспортирована в {filename}")


# Автоматический экспорт при запуске в development режиме
if __name__ == "__main__" and not os.getenv("RENDER"):
    export_to_json()

import asyncio
import os
import json
import logging
import hashlib
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8366282845:AAF7_qzwROEJd0eBrlzcloe8RsyzwBNoVek")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7025174146))

# Free-Kassa настройки
FK_SHOP_ID = os.environ.get("FK_SHOP_ID", "")
FK_API_KEY = os.environ.get("FK_API_KEY", "")
FK_SECRET_KEY = os.environ.get("FK_SECRET_KEY", "")  # Секретное слово 1
FK_SECRET_KEY2 = os.environ.get("FK_SECRET_KEY2", "")  # Секретное слово 2

if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    exit(1)

# ==================== VPN ПЛАНЫ ====================
VPN_PLANS = [
    {
        "id": 1,
        "name": "🔐 VPN Premium 1 месяц",
        "price": 299,
        "duration": "30 дней",
        "description": "• 50+ серверов\n• До 3 устройств\n• Безлимитный трафик"
    },
    {
        "id": 2,
        "name": "🚀 VPN Premium 3 месяца",
        "price": 799,
        "duration": "90 дней",
        "description": "• Экономия 10%\n• До 5 устройств\n• Приоритетная поддержка"
    },
    {
        "id": 3,
        "name": "👑 VPN Premium 1 год",
        "price": 2499,
        "duration": "365 дней",
        "description": "• Экономия 30%\n• Неограниченно устройств\n• Персональный сервер"
    }
]

# ==================== БАЗА ДАННЫХ ====================
os.makedirs("data", exist_ok=True)
ORDERS_FILE = "data/orders.json"
KEYS_FILE = "data/keys.json"


def load_orders():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
    return {"orders": []}


def save_order(user_id, username, plan_id, amount, status="pending"):
    orders = load_orders()
    order_id = len(orders["orders"]) + 1

    order = {
        "id": order_id,
        "user_id": user_id,
        "username": username,
        "plan_id": plan_id,
        "amount": amount,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "comment": f"Order-{order_id}-User-{user_id}"
    }

    orders["orders"].append(order)

    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка сохранения заказа: {e}")
        return None

    return order_id


def update_order_status(order_id, status, vpn_key=None):
    orders = load_orders()

    for order in orders["orders"]:
        if order["id"] == order_id:
            order["status"] = status
            if vpn_key:
                order["vpn_key"] = vpn_key
            order["completed_at"] = datetime.now().isoformat() if status == "completed" else None

            try:
                with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(orders, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                logger.error(f"Ошибка обновления заказа: {e}")

    return False


def load_keys():
    if not os.path.exists(KEYS_FILE):
        default_keys = {
            "keys": [
                {"key": "VPN-KEY-001-30DAYS", "plan_id": 1, "used": False},
                {"key": "VPN-KEY-002-30DAYS", "plan_id": 1, "used": False},
                {"key": "VPN-KEY-003-30DAYS", "plan_id": 1, "used": False},
                {"key": "VPN-KEY-004-90DAYS", "plan_id": 2, "used": False},
                {"key": "VPN-KEY-005-90DAYS", "plan_id": 2, "used": False},
                {"key": "VPN-KEY-006-365DAYS", "plan_id": 3, "used": False},
                {"key": "VPN-KEY-007-365DAYS", "plan_id": 3, "used": False},
            ]
        }
        try:
            with open(KEYS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_keys, f, indent=2, ensure_ascii=False)
            logger.info("✅ Создан файл keys.json")
        except Exception as e:
            logger.error(f"❌ Ошибка создания keys.json: {e}")
        return default_keys

    try:
        with open(KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки ключей: {e}")
        return {"keys": []}


def get_available_key(plan_id):
    keys_data = load_keys()

    for key_item in keys_data["keys"]:
        if key_item["plan_id"] == plan_id and not key_item["used"]:
            key_item["used"] = True
            try:
                with open(KEYS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(keys_data, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ Ключ {key_item['key']} выдан для тарифа {plan_id}")
                return key_item["key"]
            except Exception as e:
                logger.error(f"❌ Ошибка обновления ключа: {e}")

    logger.error(f"❌ Нет свободных ключей для тарифа {plan_id}")
    return None


# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ==============
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================== КОМАНДЫ БОТА ====================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛒 Купить VPN", callback_data="show_plans"))
    keyboard.add(InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"))
    keyboard.add(InlineKeyboardButton(text="❓ Помощь", callback_data="help"))

    if message.from_user.id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton(text="👑 Админ", callback_data="admin"))

    keyboard.adjust(2)

    await message.answer(
        "🔐 <b>Добро пожаловать в VPN SHOP!</b>\n\n"
        "Безопасный и быстрый VPN с автоматической выдачей ключей.\n\n"
        "Выберите действие:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "show_plans")
async def show_plans(callback: types.CallbackQuery):
    keyboard = InlineKeyboardBuilder()

    for plan in VPN_PLANS:
        keyboard.add(InlineKeyboardButton(
            text=f"{plan['name']} - {plan['price']}₽",
            callback_data=f"plan_{plan['id']}"
        ))

    keyboard.adjust(1)
    await callback.message.edit_text(
        "🎯 <b>Выберите тарифный план:</b>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("plan_"))
async def plan_detail(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    plan = next(p for p in VPN_PLANS if p["id"] == plan_id)

    user = callback.from_user
    order_id = save_order(user.id, user.username, plan_id, plan["price"])

    if not order_id:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return

    # Генерируем ссылку на оплату Free-Kassa
    comment = f"Order-{order_id}-User-{user.id}"
    payment_url = generate_fk_payment_link(order_id, plan['price'], user.id)

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text=f"💳 Оплатить {plan['price']}₽",
        url=payment_url
    ))
    keyboard.add(InlineKeyboardButton(
        text="✅ Я оплатил",
        callback_data=f"check_{order_id}"
    ))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="show_plans"))
    keyboard.adjust(1)

    text = f"""
<b>{plan['name']}</b>

💰 <b>Цена:</b> {plan['price']}₽
⏳ <b>Срок:</b> {plan['duration']}

{plan['description']}

<b>📝 Инструкция:</b>
1. Нажмите "💳 Оплатить {plan['price']}₽"
2. Введите <b>точную сумму {plan['price']}₽</b>
3. <b>НЕ МЕНЯЙТЕ комментарий:</b>
   <code>{comment}</code>
4. Оплатите
5. Вернитесь и нажмите "✅ Я оплатил"

<code>⚠️ Ключ придет автоматически после оплаты
⚠️ Не меняйте сумму и комментарий!</code>
"""

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer(f"✅ Заказ #{order_id} создан")


def generate_fk_payment_link(order_id, amount, user_id):
    """Генерирует ссылку на оплату через FK Wallet"""
    comment = f"Order-{order_id}-User-{user_id}"
    
    # Параметры для FK Wallet
    params = {
        'merchant_id': FK_SHOP_ID,
        'amount': amount,
        'order_id': comment,  # Важно: order_id вместо o
        'currency': 'RUB',
        'language': 'ru',
        'wallet': 'true',  # Флаг что это FK Wallet
    }
    
    # Подпись для FK Wallet
    sign_str = f"{FK_SHOP_ID}:{amount}:{FK_SECRET_KEY}:{comment}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    params['sign'] = sign
    
    # URL для FK Wallet
    base_url = "https://fkwallet.free-kassa.ru/pay/"
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    
    return f"{base_url}?{query_string}"


@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    await callback.message.answer(
        f"✅ <b>Заказ #{order_id} принят в обработку</b>\n\n"
        f"Платеж проверяется автоматически.\n"
        f"Как только Free-Kassa подтвердит оплату, вы получите ключ.\n\n"
        f"<i>Обычно это занимает 1-3 минуты...</i>",
        parse_mode="HTML"
    )
    await callback.answer()


# Остальные обработчики (my_orders, help, admin и т.д.) остаются как были
# ... (вставьте сюда код из предыдущих сообщений для этих функций)

# ==================== FREE-KASSA ВЕБХУК ===============
def verify_fk_wallet_signature(data):
    """Проверка подписи FK Wallet"""
    sign_str = f"{data.get('merchant_id')}:{data.get('amount')}:{FK_SECRET_KEY}:{data.get('order_id')}"
    expected_signature = hashlib.md5(sign_str.encode()).hexdigest().lower()
    received_signature = data.get('sign', '').lower()
    
    return expected_signature == received_signature


async def freekassa_webhook(request):
    """Вебхук для FK Wallet"""
    try:
        # Получаем данные
        if request.method == 'GET':
            data = dict(request.query)
        else:
            data = dict(await request.post())
        
        logger.info(f"📥 FK Wallet вебхук: {data}")
        
        # Проверяем подпись
        if not verify_fk_wallet_signature(data):
            logger.warning("❌ Неверная подпись FK Wallet")
            return web.Response(text='ERROR: Invalid signature', status=400)
        
        # Извлекаем данные
        amount = float(data.get('amount', 0))
        order_desc = data.get('order_id', '')
        
        # Парсим комментарий: Order-{id}-User-{user_id}
        import re
        order_match = re.search(r'Order-(\d+)-User-(\d+)', order_desc)
        
        if order_match:
            order_id = int(order_match.group(1))
            user_id = int(order_match.group(2))
            
            # Находим заказ
            orders = load_orders()
            order = next((o for o in orders["orders"] if o["id"] == order_id), None)
            
            if order and order["status"] == "pending":
                # Проверяем сумму (допуск 5 руб)
                if abs(amount - order["amount"]) <= 5:
                    # Ищем свободный ключ
                    vpn_key = get_available_key(order["plan_id"])
                    
                    if vpn_key:
                        # Обновляем заказ с ключом
                        update_order_status(order_id, "completed", vpn_key)
                        
                        # Уведомляем админа
                        try:
                            plan = next(p for p in VPN_PLANS if p['id'] == order['plan_id'])
                            await bot.send_message(
                                ADMIN_ID,
                                f"💰 <b>✅ ОПЛАТА ЧЕРЕЗ FK WALLET</b>\n\n"
                                f"📦 Заказ: #{order_id}\n"
                                f"👤 Пользователь: @{order['username']}\n"
                                f"🎯 Тариф: {plan['name']}\n"
                                f"💳 Сумма: {amount}₽\n"
                                f"🔑 Ключ: <code>{vpn_key}</code>\n"
                                f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"❌ Не могу уведомить админа: {e}")
                        
                        # Отправляем ключ пользователю
                        try:
                            plan = next(p for p in VPN_PLANS if p['id'] == order['plan_id'])
                            await bot.send_message(
                                user_id,
                                f"🎉 <b>✅ Оплата подтверждена!</b>\n\n"
                                f"📦 Заказ: <b>#{order_id}</b>\n"
                                f"🎯 Тариф: {plan['name']}\n"
                                f"⏳ Срок: {plan['duration']}\n"
                                f"💳 Сумма: {amount}₽\n\n"
                                f"<b>🔑 Ваш VPN ключ:</b>\n"
                                f"<code>{vpn_key}</code>\n\n"
                                f"<b>📦 Как активировать:</b>\n"
                                f"1. Скачайте приложение VPN\n"
                                f"2. Вставьте этот ключ в настройки\n"
                                f"3. Нажмите 'Подключиться'\n\n"
                                f"<i>Спасибо за покупку! ❤️</i>",
                                parse_mode="HTML"
                            )
                            logger.info(f"✅ Ключ отправлен пользователю {user_id}")
                        except Exception as e:
                            logger.error(f"❌ Не могу отправить ключ {user_id}: {e}")
                            await bot.send_message(
                                ADMIN_ID,
                                f"⚠️ Ключ не отправлен пользователю {user_id}\n"
                                f"Ключ: {vpn_key}"
                            )
                    else:
                        # Нет свободных ключей
                        logger.error(f"❌ Нет ключей для тарифа {order['plan_id']}")
                        await bot.send_message(
                            ADMIN_ID,
                            f"🚨 Нет ключей для тарифа {order['plan_id']}!"
                        )
        
        # FK Wallet ожидает YES в ответ
        return web.Response(text='YES', status=200)
        
    except Exception as e:
        logger.error(f"❌ Ошибка вебхука FK Wallet: {e}")
        return web.Response(text='ERROR', status=500)


# ==================== HEALTH CHECK ====================
async def health_check(request):
    return web.Response(text="✅ VPN Bot работает!", status=200)


async def start_web_server():
    """Запуск веб-сервера"""
    app = web.Application()

    # Вебхук Free-Kassa
    app.router.add_get('/webhook/freekassa', freekassa_webhook)
    app.router.add_post('/webhook/freekassa', freekassa_webhook)

    # Health checks
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"🌐 Веб-сервер запущен на порту {port}")
    logger.info(f"🔗 Вебхук Free-Kassa: https://ваш-бот.onrender.com/webhook/freekassa")

    # Создаем базу ключей
    load_keys()

    return runner


# ==================== ЗАПУСК ========================
async def main():
    logger.info("🚀 Запуск VPN Shop бота с Free-Kassa...")
    logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...")
    logger.info(f"👑 Админ ID: {ADMIN_ID}")

    if FK_SHOP_ID and FK_SECRET_KEY and FK_SECRET_KEY2:
        logger.info("✅ Free-Kassa настройки установлены")
    else:
        logger.warning("⚠️ Free-Kassa настройки не установлены!")

    # Запускаем веб-сервер
    runner = await start_web_server()

    try:
        # Запускаем бота
        logger.info("🤖 Бот запущен и ожидает сообщений...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")
    finally:
        await runner.cleanup()


if __name__ == "__main__":

    asyncio.run(main())

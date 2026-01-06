import asyncio
import os
import json
import logging
import hmac
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
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8380970259:AAHWmisezXdQsOyt8h6STBHuDVv7N5b1UR8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7025174146))
DONATEPAY_SECRET = os.environ.get("DONATEPAY_SECRET", "")

if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    exit(1)

if not DONATEPAY_SECRET:
    logger.warning("⚠️ DONATEPAY_SECRET не установлен, вебхуки работать не будут!")

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
    """Загружает базу заказов"""
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
    return {"orders": []}


def save_order(user_id, username, plan_id, amount, status="pending"):
    """Создает новый заказ"""
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
    """Обновляет статус заказа"""
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
    """Загружает базу ключей"""
    if not os.path.exists(KEYS_FILE):
        # Создаем файл с примером ключей
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
            logger.info("✅ Создан файл keys.json с примерами ключей")
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
    """Находит свободный ключ для тарифа"""
    keys_data = load_keys()

    for key_item in keys_data["keys"]:
        if key_item["plan_id"] == plan_id and not key_item["used"]:
            # Помечаем как использованный
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

    # Ссылка на DonatePay с комментарием
    comment = f"Order-{order_id}-User-{user.id}"
    donatepay_url = f"https://donatepay.ru/donate/773442?amount={plan['price']}&comment={comment}"

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text=f"💳 Оплатить {plan['price']}₽",
        url=donatepay_url
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


@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    await callback.message.answer(
        f"✅ <b>Заказ #{order_id} принят в обработку</b>\n\n"
        f"Платеж проверяется автоматически.\n"
        f"Как только DonatePay подтвердит оплату, вы получите ключ.\n\n"
        f"<i>Обычно это занимает 1-3 минуты...</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = load_orders()

    user_orders = [o for o in orders["orders"] if o["user_id"] == user_id]

    if not user_orders:
        text = "📭 У вас еще нет заказов."
    else:
        text = f"📋 <b>Ваши заказы ({len(user_orders)}):</b>\n\n"

        for order in user_orders[-5:]:  # Последние 5 заказов
            plan = next(p for p in VPN_PLANS if p["id"] == order["plan_id"])
            status_icon = "✅" if order["status"] == "completed" else "⏳"

            text += f"{status_icon} <b>Заказ #{order['id']}</b>\n"
            text += f"   Тариф: {plan['name']}\n"
            text += f"   Сумма: {order['amount']}₽\n"
            text += f"   Статус: {order['status']}\n"

            if order.get("vpn_key"):
                text += f"   🔑 Ключ: <code>{order['vpn_key']}</code>\n"

            text += f"   📅 Дата: {order['created_at'][:16]}\n\n"

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛒 Купить еще", callback_data="show_plans"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await start_cmd(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "help")
async def help_handler(callback: types.CallbackQuery):
    text = """
<b>❓ Как купить VPN:</b>

1. <b>Выберите тариф</b> → укажите срок
2. <b>Оплатите</b> по ссылке DonatePay
3. <b>Не меняйте</b> сумму и комментарий!
4. <b>Получите ключ</b> автоматически

<b>⚠️ Важно:</b>
• Оплачивайте точную сумму из заказа
• Не редактируйте комментарий к платежу
• Ключ придет в этом чате автоматически

<b>⏳ Сроки:</b>
• Проверка платежа: 1-3 минуты
• Выдача ключа: мгновенно после проверки

<b>🆘 Поддержка:</b>
По всем вопросам: @ваша_поддержка
"""

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛒 Купить VPN", callback_data="show_plans"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    orders = load_orders()
    completed = len([o for o in orders["orders"] if o["status"] == "completed"])
    pending = len([o for o in orders["orders"] if o["status"] == "pending"])

    # Загружаем ключи для статистики
    keys_data = load_keys()
    total_keys = len(keys_data["keys"])
    used_keys = len([k for k in keys_data["keys"] if k["used"]])
    free_keys = total_keys - used_keys

    text = f"""
<b>👑 Админ панель VPN SHOP</b>

📊 <b>Статистика заказов:</b>
• Всего заказов: {len(orders["orders"])}
• Завершено: {completed}
• Ожидают: {pending}

🗝️ <b>Статистика ключей:</b>
• Всего ключей: {total_keys}
• Использовано: {used_keys}
• Свободно: {free_keys}

<b>⚙️ Быстрые действия:</b>
"""

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📦 Все заказы", callback_data="admin_orders"))
    keyboard.add(InlineKeyboardButton(text="🔑 Добавить ключи", callback_data="admin_add_keys"))
    keyboard.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="🚀 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "admin_add_keys")
async def admin_add_keys(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    text = """
<b>🔑 Добавление ключей</b>

Чтобы добавить ключи, отредактируйте файл <code>data/keys.json</code>

<b>Формат ключа:</b>
<code>
{
  "key": "ВАШ_КЛЮЧ_ВПН",
  "plan_id": 1,
  "used": false
}
</code>

<b>plan_id:</b>
• 1 - 1 месяц (299₽)
• 2 - 3 месяца (799₽)
• 3 - 1 год (2499₽)

<b>Пример команд для Render:</b>
1. Зайдите в Dashboard Render
2. Нажмите "Shell"
3. Отредактируйте файл:
<code>nano data/keys.json</code>
"""

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin"))
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    orders = load_orders()
    keys_data = load_keys()

    # Статистика по тарифам
    stats = {}
    total_revenue = 0

    for order in orders["orders"]:
        if order["status"] == "completed":
            plan_id = order["plan_id"]
            stats[plan_id] = stats.get(plan_id, 0) + 1
            total_revenue += order["amount"]

    text = f"""
<b>📊 Детальная статистика</b>

💰 <b>Общая выручка:</b> {total_revenue}₽

<b>📈 Продажи по тарифам:</b>
"""

    for plan in VPN_PLANS:
        count = stats.get(plan["id"], 0)
        revenue = count * plan["price"]
        text += f"• {plan['name']}: {count} шт. ({revenue}₽)\n"

    # Статистика ключей по тарифам
    text += "\n<b>🗝️ Ключи по тарифам:</b>\n"
    for plan in VPN_PLANS:
        total = len([k for k in keys_data["keys"] if k["plan_id"] == plan["id"]])
        used = len([k for k in keys_data["keys"] if k["plan_id"] == plan["id"] and k["used"]])
        free = total - used
        text += f"• {plan['name']}: {used}/{total} (свободно: {free})\n"

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin"))
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


# ==================== DONATEPAY ВЕБХУК ===============
def verify_donatepay_signature(data, signature):
    """Проверка подписи DonatePay"""
    if not DONATEPAY_SECRET:
        return False

    # DonatePay использует HMAC-SHA256
    secret = DONATEPAY_SECRET.encode('utf-8')

    # Создаем строку для подписи
    message = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    # Создаем HMAC
    expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


async def donatepay_webhook(request):
    """Вебхук для DonatePay с АВТОВЫДАЧЕЙ"""
    try:
        # Получаем данные
        data = await request.json()

        # Получаем подпись из заголовков
        signature = request.headers.get('X-DonatePay-Signature', '')

        # Проверяем подпись
        if DONATEPAY_SECRET and not verify_donatepay_signature(data, signature):
            logger.warning("❌ Неверная подпись DonatePay")
            return web.Response(text='Invalid signature', status=400)

        logger.info(f"📥 DonatePay вебхук получен")

        # Обрабатываем уведомление о донате
        if data.get('type') == 'donation':
            donation = data.get('donation', {})

            amount = float(donation.get('sum', 0))
            comment = donation.get('comment', '')
            transaction_id = donation.get('id', '')

            # Парсим комментарий: Order-{id}-User-{user_id}
            import re
            order_match = re.search(r'Order-(\d+)-User-(\d+)', comment)

            if order_match:
                order_id = int(order_match.group(1))
                user_id = int(order_match.group(2))

                # Находим заказ
                orders = load_orders()
                order = next((o for o in orders["orders"] if o["id"] == order_id), None)

                if order and order["status"] == "pending":
                    # Проверяем сумму (допуск 5 руб)
                    if abs(amount - order["amount"]) <= 5:
                        # ИЩЕМ СВОБОДНЫЙ КЛЮЧ ДЛЯ ЭТОГО ТАРИФА
                        vpn_key = get_available_key(order["plan_id"])

                        if vpn_key:
                            # Обновляем заказ с ключом
                            update_order_status(order_id, "completed", vpn_key)

                            # Уведомляем админа
                            try:
                                plan_name = next(p['name'] for p in VPN_PLANS if p['id'] == order['plan_id'])
                                await bot.send_message(
                                    ADMIN_ID,
                                    f"💰 <b>✅ АВТООПЛАТА + АВТОВЫДАЧА</b>\n\n"
                                    f"📦 Заказ: #{order_id}\n"
                                    f"👤 Пользователь: @{order['username']} (ID: {user_id})\n"
                                    f"🎯 Тариф: {plan_name}\n"
                                    f"💳 Сумма: {amount}₽\n"
                                    f"🔑 Ключ: <code>{vpn_key}</code>\n"
                                    f"📝 Транзакция: {transaction_id}\n"
                                    f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}",
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                logger.error(f"❌ Не могу уведомить админа: {e}")

                            # ОТПРАВЛЯЕМ КЛЮЧ ПОЛЬЗОВАТЕЛЮ
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
                                    f"<i>Спасибо за покупку! ❤️\nПриятного использования!</i>",
                                    parse_mode="HTML"
                                )
                                logger.info(f"✅ Ключ отправлен пользователю {user_id}")
                            except Exception as e:
                                logger.error(f"❌ Не могу отправить ключ {user_id}: {e}")
                                # Если не удалось отправить, сохраняем для ручной выдачи
                                try:
                                    await bot.send_message(
                                        ADMIN_ID,
                                        f"⚠️ <b>Ключ не отправлен пользователю</b>\n\n"
                                        f"👤 ID: {user_id}\n"
                                        f"📦 Заказ: #{order_id}\n"
                                        f"🔑 Ключ: <code>{vpn_key}</code>\n\n"
                                        f"<i>Отправьте ключ вручную</i>",
                                        parse_mode="HTML"
                                    )
                                except:
                                    pass
                        else:
                            # Нет свободных ключей
                            logger.error(f"❌ Нет свободных ключей для тарифа {order['plan_id']}")
                            try:
                                await bot.send_message(
                                    ADMIN_ID,
                                    f"🚨 <b>❌ НЕТ КЛЮЧЕЙ ДЛЯ АВТОВЫДАЧИ!</b>\n\n"
                                    f"📦 Заказ: #{order_id}\n"
                                    f"👤 Пользователь: @{order['username']}\n"
                                    f"🎯 Тариф ID: {order['plan_id']}\n"
                                    f"💳 Сумма: {amount}₽\n\n"
                                    f"⚠️ <b>Добавьте ключи вручную!</b>\n"
                                    f"Файл: <code>data/keys.json</code>",
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                logger.error(f"❌ Не могу уведомить админа об отсутствии ключей: {e}")
                    else:
                        logger.warning(f"⚠️ Неправильная сумма: {amount}₽ вместо {order['amount']}₽")
                else:
                    logger.warning(f"⚠️ Заказ #{order_id} не найден или уже обработан")
            else:
                logger.warning(f"⚠️ Неверный формат комментария: {comment}")

        return web.Response(text='OK', status=200)

    except json.JSONDecodeError:
        logger.error("❌ Неверный JSON в вебхуке")
        return web.Response(text='Invalid JSON', status=400)
    except Exception as e:
        logger.error(f"❌ Ошибка вебхука: {e}")
        return web.Response(text='Error', status=500)


# ==================== HEALTH CHECK ====================
async def health_check(request):
    return web.Response(text="✅ VPN Bot работает!", status=200)


async def start_web_server():
    """Запуск веб-сервера для Render"""
    app = web.Application()

    # Вебхук DonatePay
    app.router.add_post('/webhook/donatepay', donatepay_webhook)

    # Health checks
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"🌐 Веб-сервер запущен на порту {port}")

    # Выводим URL для вебхука
    bot_url = os.environ.get('RENDER_EXTERNAL_URL', f'http://localhost:{port}')
    webhook_url = f"{bot_url}/webhook/donatepay"
    logger.info(f"🔗 Вебхук URL для DonatePay: {webhook_url}")

    # Проверяем базу ключей
    load_keys()  # Создаст файл если его нет

    return runner


# ==================== ЗАПУСК ========================
async def main():
    logger.info("🚀 Запуск VPN Shop бота...")
    logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...")
    logger.info(f"👑 Админ ID: {ADMIN_ID}")

    if DONATEPAY_SECRET:
        logger.info("✅ DonatePay секретный ключ установлен")
    else:
        logger.warning("⚠️ DonatePay секретный ключ НЕ установлен")

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
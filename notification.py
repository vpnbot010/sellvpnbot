from aiogram import Bot
from config import ADMIN_IDS

async def notify_admins(bot: Bot, message: str):
    """Отправка уведомления всем админам"""
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки уведомления админу {admin_id}: {e}")

async def notify_user(bot: Bot, user_id: int, message: str):
    """Отправка уведомления пользователю"""
    try:
        await bot.send_message(user_id, message, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

# Шаблоны уведомлений
def order_confirmed_template(order_id: int, case_name: str, gold_amount: float):
    return (
        f"✅ <b>Заказ подтвержден!</b>\n\n"
        f"🛒 Заказ #{order_id}\n"
        f"🎁 Кейс: {case_name}\n"
        f"💰 Начислено: {gold_amount} голды\n\n"
        f"<i>Кейс теперь доступен в вашем инвентаре</i>"
    )

def withdrawal_confirmed_template(withdrawal_id: int, amount: float):
    return (
        f"✅ <b>Вывод подтвержден!</b>\n\n"
        f"📤 Заявка #{withdrawal_id}\n"
        f"💰 Сумма: {amount} RUB\n"
        f"💵 Выплачено: {amount * 0.8:.2f} голды\n\n"
        f"<i>Скин куплен в игре. Спасибо за использование нашего сервиса!</i>"
    )

def new_order_admin_template(order_id: int, username: str, user_id: int, case_name: str, amount: float):
    return (
        f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
        f"👤 Пользователь: @{username or 'без username'}\n"
        f"🆔 ID: {user_id}\n"
        f"🎁 Кейс: {case_name}\n"
        f"💰 Сумма: {amount}₽\n\n"
        f"Ожидает подтверждения оплаты"
    )

def new_withdrawal_admin_template(withdrawal_id: int, username: str, user_id: int, amount: float, game_nickname: str):
    return (
        f"📤 <b>Новая заявка на вывод #{withdrawal_id}</b>\n\n"
        f"👤 Пользователь: @{username or 'без username'}\n"
        f"🆔 ID: {user_id}\n"
        f"🎮 Ник в игре: {game_nickname}\n"
        f"💰 Сумма: {amount} голды\n"
        f"💵 К выплате: {amount * 0.8:.2f} RUB\n\n"
        f"<b>Требуется купить скин в игре</b>"
    )
from aiogram import Router, F
from aiogram.handlers import message
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS, CASES
from keyboards.buttons import admin_order_menu, admin_withdrawal_menu
from database.db import Database

router = Router()
db = Database()


class AdminStates(StatesGroup):
    adding_promo = State()
    deleting_promo = State()
    toggling_promo = State()


# ========== АДМИН-ПАНЕЛЬ ==========
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return

    pending_orders = db.get_pending_orders()
    pending_withdrawals = db.get_pending_withdrawals()

    stats_text = (
        f"👑 <b>Панель администратора</b>\n\n"
        f"📊 Статистика:\n"
        f"🛒 Ожидает оплаты: {len(pending_orders)}\n"
        f"📤 Ожидает выплаты: {len(pending_withdrawals)}\n\n"
        f"<i>Используйте кнопки ниже:</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 К промокодам", callback_data="admin_promocodes"),
                InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")
            ],
            [
                InlineKeyboardButton(text="📤 К выводам", callback_data="admin_withdrawals"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
            ]
        ]
    )

    await message.answer(stats_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin")
async def back_to_admin(callback: CallbackQuery):
    """Возврат в админ-панель"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    pending_orders = db.get_pending_orders()
    pending_withdrawals = db.get_pending_withdrawals()

    stats_text = (
        f"👑 <b>Панель администратора</b>\n\n"
        f"📊 Статистика:\n"
        f"🛒 Ожидает оплаты: {len(pending_orders)}\n"
        f"📤 Ожидает выплаты: {len(pending_withdrawals)}\n\n"
        f"<i>Используйте кнопки ниже:</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 К промокодам", callback_data="admin_promocodes"),
                InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")
            ],
            [
                InlineKeyboardButton(text="📤 К выводам", callback_data="admin_withdrawals"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
            ]
        ]
    )

    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="HTML")


# ========== ОБРАБОТЧИКИ ОСНОВНЫХ КНОПОК АДМИН-ПАНЕЛИ ==========
@router.message(Command("orders"))
@router.callback_query(F.data == "admin_orders")
async def show_orders(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
        callback = event
    else:
        user_id = event.from_user.id
        message = event
        callback = None

    if user_id not in ADMIN_IDS:
        if callback:
            await callback.answer("⛔ Нет доступа")
        return

    orders = db.get_pending_orders()

    if not orders:
        text = "✅ Нет заказов, ожидающих обработки"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin")]]
        )
        if callback:
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return

    for order in orders:
        case = CASES.get(order['case_id'], {})
        order_text = (
            f"🛒 <b>Заказ #{order['id']}</b>\n\n"
            f"👤 Пользователь: @{order['username'] or 'без username'}\n"
            f"🆔 ID: {order['telegram_id']}\n"
            f"🎁 Кейс: {case.get('name', 'Неизвестно')}\n"
            f"💰 Сумма: {order['amount']}₽\n"
            f"📅 Дата: {order['created_at']}\n\n"
            f"<b>Статус: {order['status']}</b>"
        )

        if callback:
            await callback.message.answer(
                order_text,
                reply_markup=admin_order_menu(order['id'], order['telegram_id']),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                order_text,
                reply_markup=admin_order_menu(order['id'], order['telegram_id']),
                parse_mode="HTML"
            )


@router.message(Command("withdrawals"))
@router.callback_query(F.data == "admin_withdrawals")
async def show_withdrawals(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
        callback = event
    else:
        user_id = event.from_user.id
        message = event
        callback = None

    if user_id not in ADMIN_IDS:
        if callback:
            await callback.answer("⛔ Нет доступа")
        return

    withdrawals = db.get_pending_withdrawals()

    if not withdrawals:
        text = "✅ Нет заявок на вывод"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin")]]
        )
        if callback:
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return

    for withdraw in withdrawals:
        withdraw_text = (
            f"📤 <b>Вывод #{withdraw['id']}</b>\n\n"
            f"👤 Пользователь: @{withdraw['username'] or 'без username'}\n"
            f"🆔 ID: {withdraw['telegram_id']}\n"
            f"🎮 Ник в игре: <code>{withdraw['game_nickname']}</code>\n"
            f"💰 Сумма: {withdraw['amount']} RUB\n"
            f"💵 К выплате: {float(withdraw['amount']):.2f} RUB (без комиссии)\n\n"
            f"🎯 Скин: {withdraw['skin_name']}\n"
            f"🏷 Цена в игре: {withdraw['skin_price']} голды\n"
            f"📅 Дата: {withdraw['created_at']}"
        )

        if withdraw.get('screenshot_url'):
            try:
                await message.bot.send_photo(
                    message.chat.id,
                    photo=withdraw['screenshot_url'],
                    caption=withdraw_text,
                    reply_markup=admin_withdrawal_menu(withdraw['id'], withdraw['telegram_id']),
                    parse_mode="HTML"
                )
                continue
            except:
                pass

        if callback:
            await callback.message.answer(
                withdraw_text,
                reply_markup=admin_withdrawal_menu(withdraw['id'], withdraw['telegram_id']),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                withdraw_text,
                reply_markup=admin_withdrawal_menu(withdraw['id'], withdraw['telegram_id']),
                parse_mode="HTML"
            )


@router.message(Command("promocodes"))
@router.callback_query(F.data == "admin_promocodes")
async def admin_promocodes(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
        callback = event
    else:
        user_id = event.from_user.id
        message = event
        callback = None

    if user_id not in ADMIN_IDS:
        if callback:
            await callback.answer("⛔ Нет доступа")
        return

    promocodes = db.get_all_promocodes()

    if not promocodes:
        text = "📋 <b>Промокоды</b>\n\nНет активных промокодов."
    else:
        text = "📋 <b>Промокоды</b>\n\n"
        for promo in promocodes:
            try:
                import json
                used_by = json.loads(promo.get('used_by', '[]'))
            except:
                used_by = []

            discount = float(promo.get('discount', 0.2)) * 100
            status = "✅ Активен" if promo.get('is_active', 1) else "❌ Неактивен"
            text += f"🎟 <code>{promo['code']}</code>\n"
            text += f"   Скидка: {discount:.0f}%\n"
            text += f"   Статус: {status}\n"
            text += f"   Использовали: {len(used_by)} чел.\n"
            text += "────────────────────\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить", callback_data="admin_add_promo"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data="admin_delete_promo")
            ],
            [
                InlineKeyboardButton(text="✅ Активировать", callback_data="admin_activate_promo"),
                InlineKeyboardButton(text="❌ Деактивировать", callback_data="admin_deactivate_promo")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin")]
        ]
    )

    if callback:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("stats"))
@router.callback_query(F.data == "admin_stats")
async def show_stats(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    else:
        user_id = event.from_user.id
        message = event

    if user_id not in ADMIN_IDS:
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Нет доступа")
        return

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM orders WHERE status = 'completed'")
    total_revenue = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'completed'")
    total_withdrawals = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE status = 'completed'")
    total_paid_out = cursor.fetchone()[0] or 0

    conn.close()

    stats_text = (
        f"📊 <b>Общая статистика</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"🛒 Заказов: <b>{total_orders}</b>\n"
        f"💰 Выручка: <b>{total_revenue:.2f}₽</b>\n"
        f"📤 Выводов: <b>{total_withdrawals}</b>\n"
        f"💸 Выплачено: <b>{total_paid_out:.2f} голды</b>\n\n"
        f"<b>Кейсы по популярности:</b>\n"
    )

    for case_id, case_data in CASES.items():
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM orders WHERE case_id = ? AND status = 'completed'",
            (case_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()

        if count > 0:
            stats_text += f"• {case_data['name']}: {count} продаж\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin")]]
    )

    if isinstance(event, CallbackQuery):
        await message.edit_text(stats_text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(stats_text, reply_markup=kb, parse_mode="HTML")


# ========== ОБРАБОТЧИКИ ДЛЯ КНОПОК В РАЗДЕЛАХ ==========
@router.callback_query(F.data.startswith("admin_confirm_"))
async def confirm_order(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    try:
        order_id = int(callback.data.split("_")[2])
    except:
        await callback.answer("❌ Ошибка в данных")
        return

    orders = db.get_pending_orders()
    order = None
    for o in orders:
        if o['id'] == order_id:
            order = o
            break

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    db.update_order_status(order_id, "completed")
    case = CASES.get(order['case_id'], {})

    case_item = {"name": case['name'], "rarity": "Case", "price": 0}
    db.add_to_inventory(order['telegram_id'], order['case_id'], case_item)

    try:
        await callback.bot.send_message(
            order['telegram_id'],
            f"✅ <b>Ваш заказ подтвержден!</b>\n\n"
            f"🎁 Кейс: {case.get('name', 'Неизвестно')}\n"
            f"🛒 Теперь кейс доступен в вашем инвентаре\n\n"
            f"<i>Перейдите в раздел 🎒 Инвентарь чтобы открыть кейс</i>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎒 Открыть инвентарь", callback_data="inventory")],
                    [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
                    [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
                ]
            ),
            parse_mode="HTML"
        )
    except:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")]]
    )

    await callback.message.edit_text(
        f"✅ <b>Заказ #{order_id} подтвержден</b>\n\n"
        f"👤 Пользователь: @{order.get('username', 'без username')}\n"
        f"🎁 Кейс: {case.get('name', 'Неизвестно')}\n"
        f"💰 Сумма: {order['amount']}₽\n"
        f"📅 Время: {order['created_at']}\n\n"
        f"<i>Кейс добавлен в инвентарь пользователя</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_reject_"))
async def reject_order(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    try:
        order_id = int(callback.data.split("_")[2])
    except:
        await callback.answer("❌ Ошибка в данных")
        return

    orders = db.get_pending_orders()
    order = None
    for o in orders:
        if o['id'] == order_id:
            order = o
            break

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    db.update_order_status(order_id, "rejected")

    try:
        await callback.bot.send_message(
            order['telegram_id'],
            "❌ <b>Ваш заказ отклонен</b>\n\n"
            f"Заказ #{order_id} был отклонен администратором.\n"
            f"Причина: оплата не поступила или была неверной.\n\n"
            f"<i>Если вы считаете, что это ошибка, свяжитесь с поддержкой</i>",
            parse_mode="HTML"
        )
    except:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")]]
    )

    await callback.message.edit_text(
        f"❌ <b>Заказ #{order_id} отклонен</b>\n\n"
        f"👤 Пользователь: @{order.get('username', 'без username')}\n"
        f"Пользователь уведомлен об отказе",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_withdraw_confirm_"))
async def confirm_withdrawal(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    try:
        withdrawal_id = int(callback.data.split("_")[3])
    except:
        await callback.answer("❌ Ошибка в данных")
        return

    db.update_withdrawal_status(withdrawal_id, "completed")

    withdrawal = db.get_withdrawal_by_id(withdrawal_id)

    if not withdrawal:
        await callback.answer("❌ Заявка не найдена")
        return

    try:
        kb_user = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
            ]
        )

        await callback.bot.send_message(
            withdrawal['telegram_id'],
            f"✅ <b>Ваш вывод подтвержден!</b>\n\n"
            f"💰 Сумма: {withdrawal['amount']} ГОЛДЫ\n"
            f"💵 Выплачено: {float(withdrawal['amount']):.2f} RUB\n"
            f"🎮 Скин куплен: {withdrawal['skin_name']}\n\n"
            f"<i>Спасибо за использование нашего сервиса! Не забывайте оставлять отзывы - мы ценим ваше мнение ❤️‍🩹</i>",
            reply_markup=kb_user,
            parse_mode="HTML"
        )
    except:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📋 К выводам", callback_data="admin_withdrawals")]]
    )

    await callback.message.edit_text(
        f"✅ <b>Вывод #{withdrawal_id} подтвержден</b>\n\n"
        f"👤 Пользователь уведомлен\n"
        f"💰 Сумма: {withdrawal['amount']} голды выплачена",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_withdraw_reject_"))
async def reject_withdrawal(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    try:
        withdrawal_id = int(callback.data.split("_")[3])
    except:
        await callback.answer("❌ Ошибка в данных")
        return

    db.update_withdrawal_status(withdrawal_id, "rejected")

    withdrawals = db.get_pending_withdrawals()
    withdrawal = None
    for w in withdrawals:
        if w['id'] == withdrawal_id:
            withdrawal = w
            break

    if not withdrawal:
        await callback.answer("❌ Заявка не найдена")
        return

    try:
        await callback.bot.send_message(
            withdrawal['telegram_id'],
            "❌ <b>Ваш вывод отклонен</b>\n\n"
            f"Заявка #{withdrawal_id} была отклонена администратором.\n"
            f"Причина: неверные данные или нарушение правил.\n\n"
            f"<i>Если вы считаете, что это ошибка, свяжитесь с поддержкой</i>",
            parse_mode="HTML"
        )
    except:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📋 К выводам", callback_data="admin_withdrawals")]]
    )

    await callback.message.edit_text(
        f"❌ <b>Вывод #{withdrawal_id} отклонен</b>\n\n"
        f"👤 Пользователь уведомлен об отказе",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ========== ПРОМОКОДЫ (УПРАВЛЕНИЕ) ==========
@router.callback_query(F.data == "admin_add_promo")
async def admin_add_promo_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    await state.set_state(AdminStates.adding_promo)
    await callback.message.edit_text(
        "➕ <b>Добавление промокода</b>\n\n"
        "Введите промокод (только заглавные буквы и цифры):\n\n"
        "<i>Используйте /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.adding_promo)
async def admin_add_promo_finish(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.text == "/cancel":
        await message.answer("❌ Добавление промокода отменено")
        await state.clear()
        return

    promo_code = message.text.strip().upper()

    if not promo_code.isalnum() or len(promo_code) < 4:
        await message.answer("❌ Неверный формат промокода. Используйте заглавные буквы и цифры (минимум 4 символа)")
        return

    db.add_promocode(promo_code)

    await message.answer(
        f"✅ Промокод <code>{promo_code}</code> добавлен\nСкидка: 20%",
        parse_mode="HTML"
    )

    await state.clear()


@router.callback_query(F.data == "admin_delete_promo")
async def admin_delete_promo_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    promocodes = db.get_all_promocodes()

    if not promocodes:
        await callback.answer("❌ Нет промокодов для удаления")
        return

    await state.set_state(AdminStates.deleting_promo)

    kb_buttons = []
    for promo in promocodes:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {promo['code']}",
                callback_data=f"admin_delete_promo_{promo['code']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_promocodes")])

    await callback.message.edit_text(
        "🗑 <b>Удаление промокода</b>\n\n"
        "Выберите промокод для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_delete_promo_"))
async def admin_delete_promo_execute(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    promo_code = callback.data.replace("admin_delete_promo_", "")
    success = db.delete_promocode(promo_code)

    if success:
        await callback.message.edit_text(
            f"✅ Промокод <code>{promo_code}</code> удален",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📋 К промокодам", callback_data="admin_promocodes")]]
            ),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Промокод не найден")

    await state.clear()


@router.callback_query(F.data == "admin_activate_promo")
async def admin_activate_promo_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    promocodes = db.get_all_promocodes()
    inactive_promos = [p for p in promocodes if not p.get('is_active', 1)]

    if not inactive_promos:
        await callback.answer("❌ Нет неактивных промокодов")
        return

    kb_buttons = []
    for promo in inactive_promos:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"✅ {promo['code']}",
                callback_data=f"admin_toggle_promo_{promo['code']}_1"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promocodes")])

    await callback.message.edit_text(
        "✅ <b>Активация промокода</b>\n\n"
        "Выберите промокод для активации:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_deactivate_promo")
async def admin_deactivate_promo_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    promocodes = db.get_all_promocodes()
    active_promos = [p for p in promocodes if p.get('is_active', 1)]

    if not active_promos:
        await callback.answer("❌ Нет активных промокодов")
        return

    kb_buttons = []
    for promo in active_promos:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"❌ {promo['code']}",
                callback_data=f"admin_toggle_promo_{promo['code']}_0"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promocodes")])

    await callback.message.edit_text(
        "❌ <b>Деактивация промокода</b>\n\n"
        "Выберите промокод для деактивации:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_toggle_promo_"))
async def admin_toggle_promo_execute(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return

    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("❌ Ошибка в данных")
        return

    promo_code = parts[3]
    try:
        status = int(parts[4])
    except:
        await callback.answer("❌ Ошибка в статусе")
        return

    success = db.toggle_promocode(promo_code, bool(status))

    if success:
        action = "активирован" if status else "деактивирован"
        await callback.message.edit_text(
            f"✅ Промокод <code>{promo_code}</code> {action}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📋 К промокодам", callback_data="admin_promocodes")]]
            ),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Промокод не найден")


# ========== ПОЛЬЗОВАТЕЛИ ==========
@router.message(Command("users"))
async def show_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде")
        return

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, telegram_id, balance, reg_date FROM users ORDER BY reg_date DESC LIMIT 10"
    )
    users = cursor.fetchall()
    conn.close()

    users_text = "👥 <b>Последние 10 пользователей:</b>\n\n"

    for user in users:
        users_text += (
            f"👤 @{user['username'] or 'нет username'}\n"
            f"🆔 ID: {user['telegram_id']}\n"
            f"💰 Баланс: {user['balance']} голды\n"
            f"📅 Регистрация: {user['reg_date'][:10]}\n"
            f"────────────────────\n"
        )

    await message.answer(users_text, parse_mode="HTML")
import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CASES
from database.db import Database

router = Router()
db = Database()


@router.message(F.text == "🎒 Инвентарь")
@router.callback_query(F.data == "inventory")
async def show_inventory(event: Message | CallbackQuery):
    """Показываем инвентарь пользователя"""
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
        callback = event
    else:
        user_id = event.from_user.id
        message = event
        callback = None

    # Получаем инвентарь
    items = db.get_inventory(user_id)

    if not items:
        text = (
            "🎒 <b>Ваш инвентарь пуст</b>\n\n"
            "Приобретите кейсы в разделе 🎁 Кейсы"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Купить кейсы", callback_data="cases")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
            ]
        )
    else:
        # Разделяем кейсы и предметы
        cases = [item for item in items if item['item_rarity'] == 'Case']
        other_items = [item for item in items if item['item_rarity'] != 'Case']

        text = "🎒 <b>Ваш инвентарь</b>\n\n"

        if cases:
            text += "<b>📦 Ваши кейсы:</b>\n"
            for case in cases:
                case_data = CASES.get(case['case_id'], {})
                text += f"• {case_data.get('name', 'Неизвестный кейс')}\n"

        if other_items:
            text += "\n<b>🎯 Ваши предметы:</b>\n"
            for item in other_items:
                text += f"• {item['item_name']} |{item['item_rarity']}| - {item['item_price']}G\n"

        text += "\nВыберите что открыть или продать:"

        # Создаем клавиатуру
        kb = InlineKeyboardBuilder()

        if cases:
            for case in cases:
                case_data = CASES.get(case['case_id'], {})
                kb.row(InlineKeyboardButton(
                    text=f"📦 {case_data.get('name', 'Кейс')}",
                    callback_data=f"open_case_{case['id']}"
                ))

        if other_items:
            for item in other_items:
                kb.row(InlineKeyboardButton(
                    text=f"🎯 {item['item_name']} - {item['item_price']}G",
                    callback_data=f"item_{item['id']}"
                ))

        kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))
        kb = kb.as_markup()

    if callback:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("open_case_"))
async def open_case_handler(callback: CallbackQuery):
    """Открываем кейс с анимацией"""
    inventory_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    # Проверяем, есть ли такой кейс в инвентаре
    item = db.get_item_by_id(inventory_id)
    if not item:
        await callback.answer("❌ Кейс не найден в инвентаре")
        return

    if item['item_rarity'] != 'Case':
        await callback.answer("❌ Это не кейс")
        return

    # Получаем данные кейса
    case_data = CASES.get(item['case_id'], {})
    case_name = case_data.get('name', 'Неизвестный кейс')

    # Стартовая анимация
    messages = [
        "🎁 <b>Загрузка кейса...</b>\n\n📦 Сканирование содержимого",
        "🔐 <b>Подключение к серверам дропа...</b>\n\n🔄 Инициализация системы",
        "🎮 <b>Запуск алгоритма выпадения...</b>\n\n⚙️ Генерация случайных значений",
        "🎯 <b>Определение предмета...</b>\n\n✨ Ожидание результата",
        "💎 <b>Почти готово!</b>\n\n🎉 Приготовьтесь увидеть дроп..."
    ]

    msg = await callback.message.answer(messages[0], parse_mode="HTML")

    # Продолжаем остальную анимацию
    for text in messages[1:]:
        await asyncio.sleep(1)
        await msg.edit_text(text, parse_mode="HTML")

    await asyncio.sleep(1)

    # Анимация кубика (нард)
    dice_message = await callback.message.bot.send_dice(
        chat_id=callback.message.chat.id,
        emoji="🎲"
    )

    # Ждем пока кубик остановится
    await asyncio.sleep(4)

    # Открываем кейс после анимации кубика
    won_item = db.open_case(inventory_id, user_id)

    if not won_item:
        await msg.edit_text("❌ Ошибка при открытии кейса")
        return

    # Удаляем сообщение с кубиком
    try:
        await callback.message.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=dice_message.message_id
        )
    except:
        pass

    # Определяем эмодзи для редкости
    rarity_emojis = {
        "Common": "⚪",
        "Uncommon": "🔵",
        "Rare": "🔷",
        "Epic": "🟣",
        "Legendary": "🟣",
        "Arcane": "🔴"
    }

    emoji = rarity_emojis.get(won_item['rarity'], "⚪")

    # Создаем клавиатуру для действий
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Продать", callback_data=f"sell_won_{won_item['price']}_{inventory_id}"),
                InlineKeyboardButton(text="💾 Оставить", callback_data="inventory")
            ],
            [InlineKeyboardButton(text="◀️ В инвентарь", callback_data="inventory")]
        ]
    )

    await msg.edit_text(
        f"🎉 <b>Поздравляем!</b>\n\n"
        f"{emoji} <b>Вы выиграли:</b> {won_item['name']}\n"
        f"🏷 <b>Редкость:</b> {won_item['rarity']}\n"
        f"💰 <b>Стоимость:</b> {won_item['price']} голды\n"
        f"📊 <b>Шанс выпадения:</b> {won_item['chance']}%\n\n"
        f"📦 <b>Открытый кейс:</b> {case_name}\n\n"
        "Выберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("item_"))
async def show_item_details(callback: CallbackQuery):
    """Показываем детали предмета"""
    item_id = int(callback.data.split("_")[1])

    # Получаем информацию о предмете
    item = db.get_item_by_id(item_id)
    if not item:
        await callback.answer("❌ Предмет не найден")
        return

    # Определяем эмодзи для редкости
    rarity_emojis = {
        "Common": "⚪",
        "Uncommon": "🔵",
        "Rare": "🔷",
        "Epic": "🟣",
        "Legendary": "🟣",
        "Arcane": "🔴"
    }

    emoji = rarity_emojis.get(item['item_rarity'], "⚪")

    # Создаем клавиатуру для действий
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Продать", callback_data=f"sell_{item_id}"),
                InlineKeyboardButton(text="💾 Оставить", callback_data="inventory")
            ],
            [InlineKeyboardButton(text="◀️ В инвентарь", callback_data="inventory")]
        ]
    )

    await callback.message.edit_text(
        f"{emoji} <b>Детали предмета:</b>\n\n"
        f"🎯 <b>Название:</b> {item['item_name']}\n"
        f"🏷 <b>Редкость:</b> {item['item_rarity']}\n"
        f"💰 <b>Стоимость:</b> {item['item_price']} голды\n\n"
        "Выберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sell_won_"))
async def sell_won_item(callback: CallbackQuery):
    """Продаем только что выигранный предмет"""
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("❌ Ошибка в данных")
        return

    price = float(parts[2])
    inventory_id = int(parts[3]) if len(parts) > 3 else None
    user_id = callback.from_user.id

    # Начисляем GOLD
    db.update_balance(user_id, price)

    # Удаляем инвентарный предмет (если есть inventory_id)
    if inventory_id:
        # Проверяем, существует ли еще предмет
        item = db.get_item_by_id(inventory_id)
        if item:
            db.remove_from_inventory(inventory_id)

    # Получаем актуальный баланс
    user = db.get_user(user_id)

    # Создаем клавиатуру
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎒 В инвентарь", callback_data="inventory")],
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ]
    )

    await callback.message.edit_text(
        f"✅ <b>Предмет продан!</b>\n\n"
        f"💰 <b>Получено:</b> {price} голды\n"
        f"🏦 <b>Баланс:</b> {user['balance']:.2f} голды\n\n"
        f"Вы можете вывести средства в разделе 💰 Вывод",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sell_"))
async def sell_item(callback: CallbackQuery):
    """Продаем предмет"""
    item_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    # Получаем информацию о предмете
    item = db.get_item_by_id(item_id)
    if not item:
        await callback.answer("❌ Предмет не найден")
        return

    # Начисляем GOLD
    db.update_balance(user_id, item['item_price'])

    # Удаляем предмет из инвентаря
    db.remove_from_inventory(item_id)

    # Получаем актуальный баланс
    user = db.get_user(user_id)

    # Создаем клавиатуру
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎒 В инвентарь", callback_data="inventory")],
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ]
    )

    await callback.message.edit_text(
        f"✅ <b>Предмет продан!</b>\n\n"
        f"🎯 <b>Продано:</b> {item['item_name']}\n"
        f"💰 <b>Получено:</b> {item['item_price']} голды\n"
        f"🏦 <b>Баланс:</b> {user['balance']:.2f} голды\n\n"
        f"Вы можете вывести средства в разделе 💰 Вывод",
        reply_markup=kb,
        parse_mode="HTML"
    )

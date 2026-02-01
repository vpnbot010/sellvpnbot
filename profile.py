from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import MIN_WITHDRAWAL
from database.db import Database

router = Router()
db = Database()


class WithdrawStates(StatesGroup):
    waiting_amount = State()
    waiting_nickname = State()
    waiting_skin_name = State()
    waiting_skin_price = State()
    waiting_screenshot = State()


@router.message(F.text == "👤 Профиль")
@router.callback_query(F.data == "profile")
async def show_profile(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id

    user = db.get_user(user_id)

    if not user:
        await message.answer("Ошибка получения профиля")
        return

    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👁‍🗨 Имя: {user['full_name'] or 'Не указано'}\n"
        f"📛 Username: @{user['username'] or 'Не указан'}\n"
        f"💰 Баланс: <b>{user['balance']:.2f} ГОЛДЫ</b>\n"
        f"📅 Регистрация: {user['reg_date'][:10]}\n\n"
        f"<b>Минимальный вывод:</b> {MIN_WITHDRAWAL} голды"
    )

    # КНОПКА НАЗАД
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ]
    )

    if isinstance(event, CallbackQuery):
        await message.edit_text(profile_text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(profile_text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "💰 Вывод")
@router.callback_query(F.data == "withdraw")
async def start_withdraw(callback: CallbackQuery, state: FSMContext):
    if isinstance(callback, CallbackQuery):
        user_id = callback.from_user.id
        message = callback.message
    else:
        user_id = callback.from_user.id
        message = callback

    user = db.get_user(user_id)

    if user['balance'] < MIN_WITHDRAWAL:
        if isinstance(callback, CallbackQuery):
            await callback.answer(f"❌ Минимальная сумма вывода: {MIN_WITHDRAWAL} голды", show_alert=True)
        else:
            await message.answer(f"❌ Минимальная сумма вывода: {MIN_WITHDRAWAL} голды")
        return

    await state.set_state(WithdrawStates.waiting_amount)
    await message.answer(
        f"💰 <b>Вывод средств</b>\n\n"
        f"Ваш баланс: <b>{user['balance']:.2f} голды</b>\n"
        f"Минимум для вывода: <b>{MIN_WITHDRAWAL} голды</b>\n"
        f"Комиссия: <b>0% (берем на себя)</b>\n\n"
        f"<i>Введите сумму для вывода (в GOLD):</i>",
        parse_mode="HTML"
    )


@router.message(WithdrawStates.waiting_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return

    user = db.get_user(message.from_user.id)

    if amount < MIN_WITHDRAWAL:
        await message.answer(f"❌ Минимальная сумма вывода: {MIN_WITHDRAWAL} голды")
        return

    if amount > user['balance']:
        await message.answer("❌ Недостаточно средств на балансе")
        return

    # РАСЧЕТ: пользователь получает 'amount' RUB
    # В игре комиссия 20% => цена скина должна быть: amount * 1.20
    game_commission = 0.20  # 20% комиссия игры
    skin_price_in_game = amount * (1 + game_commission)  # Цена для выставления в игре

    await state.update_data(
        amount=amount,  # Что получит пользователь
        amount_with_fee=amount,  # Та же сумма (комиссию берем на себя)
        skin_price_in_game=skin_price_in_game  # За сколько выставить в игре
    )

    await state.set_state(WithdrawStates.waiting_nickname)

    await message.answer(
        f"✅ Сумма принята: <b>{amount:.2f} RUB</b>\n\n"
        f"📊 <b>Расчет:</b>\n"
        f"💰 Вы получите: <b>{amount:.2f} голды</b>\n"
        f"🎮 Комиссия игры: <b>20%</b>\n"
        f"🏷 Выставьте скин за: <b>{skin_price_in_game:.2f} RUB</b>\n\n"
        f"<i>Теперь введите ваш ник в Standoff 2:</i>",
        parse_mode="HTML"
    )


@router.message(WithdrawStates.waiting_nickname)
async def process_withdraw_nickname(message: Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Ник слишком короткий")
        return

    await state.update_data(game_nickname=message.text)
    await state.set_state(WithdrawStates.waiting_skin_name)

    await message.answer(
        "<i>Введите название скина, который вы выставили на продажу в игре:</i>\n"
        "<i>Например: M4 «Predator»</i>",
        parse_mode="HTML"
    )


@router.message(WithdrawStates.waiting_skin_name)
async def process_withdraw_skin_name(message: Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Название слишком короткое")
        return

    data = await state.get_data()

    await state.update_data(skin_name=message.text)
    await state.set_state(WithdrawStates.waiting_skin_price)

    await message.answer(
        "<i>Введите цену скина в игре (в рублях):</i>\n"
        f"<i>Цена должна соответствовать сумме к получению ({data.get('amount_with_fee', 0):.2f} RUB)</i>",
        parse_mode="HTML"
    )


@router.message(WithdrawStates.waiting_skin_price)
async def process_withdraw_skin_price(message: Message, state: FSMContext):
    try:
        skin_price = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return

    data = await state.get_data()
    expected_price = data.get('skin_price_in_game', 0)

    # Проверяем, соответствует ли цена расчетной (допускаем погрешность 1 рубль)
    if abs(skin_price - expected_price) > 1:
        await message.answer(
            f"❌ <b>Неверная цена!</b>\n\n"
            f"Для вывода {data['amount']:.2f} RUB\n"
            f"Скин должен стоить: <b>{expected_price:.2f} RUB</b>\n"
            f"Вы указали: <b>{skin_price:.2f} RUB</b>\n\n"
            f"<i>Проверьте расчет: {data['amount']:.2f} × 1.20 = {expected_price:.2f} RUB</i>",
            parse_mode="HTML"
        )
        return

    await state.update_data(skin_price=skin_price)
    await state.set_state(WithdrawStates.waiting_screenshot)

    # ИСПРАВЛЕННАЯ f-СТРОКА
    await message.answer(
        f"<i>Отправьте скриншот, где видно:</i>\n"
        f"1. Ваш ник в игре\n"
        f"2. Выставленный на продажу скин\n"
        f"3. Цену скина <b>ИМЕННО {expected_price:.2f} RUB</b>\n\n"
        f"<i>Отправьте фото как файл (не сжатое)</i>",
        parse_mode="HTML"
    )


@router.message(WithdrawStates.waiting_screenshot)
async def process_withdraw_screenshot(message: Message, state: FSMContext):
    if not message.photo and not message.document:
        await message.answer("❌ Пожалуйста, отправьте скриншот")
        return

    # Получаем данные из состояния
    data = await state.get_data()

    # Создаем заявку на вывод
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    withdrawal_id = db.create_withdrawal(
        telegram_id=message.from_user.id,
        amount=data['amount'],
        game_nickname=data['game_nickname'],
        skin_name=data['skin_name'],
        skin_price=data['skin_price'],
        screenshot_url=file_id
    )

    if not withdrawal_id:
        await message.answer("❌ Ошибка создания заявки")
        await state.clear()
        return

    # Списываем средства
    db.update_balance(message.from_user.id, -data['amount'])

    # Уведомляем админа
    from config import ADMIN_IDS

    for admin_id in ADMIN_IDS:
        try:
            # Отправляем сообщение админу
            admin_text = (
                f"📤 <b>Новая заявка на вывод #{withdrawal_id}</b>\n\n"
                f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
                f"🆔 ID: {message.from_user.id}\n"
                f"🎮 Ник в игре: <code>{data['game_nickname']}</code>\n"
                f"💰 Сумма: {data['amount']} голды\n"
                f"💵 К выплате: {data['amount']} RUB (без комиссии)\n\n"  # Изменено
                f"🎯 Скин: {data['skin_name']}\n"
                f"🏷 Цена в игре: {data['skin_price']} голды\n\n"
                f"<b>Требуется купить скин в игре и подтвердить выплату</b>"
            )

            admin_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтвердить",
                            callback_data=f"admin_withdraw_confirm_{withdrawal_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="👤 Профиль",
                            url=f"tg://user?id={message.from_user.id}"
                        )
                    ]
                ]
            )

            # Отправляем фото
            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    photo=file_id,
                    caption=admin_text,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
            else:
                await message.bot.send_document(
                    admin_id,
                    document=file_id,
                    caption=admin_text,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Ошибка уведомления админа: {e}")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_withdrawals")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ]
    )

    await message.answer(
        f"✅ <b>Заявка на вывод #{withdrawal_id} создана!</b>\n\n"
        f"💰 Сумма: <b>{data['amount']} RUB</b>\n"
        f"💵 К выплате: <b>{data['amount_with_fee']:.2f} RUB</b>\n"
        f"🎮 Ник: <code>{data['game_nickname']}</code>\n"
        f"🎯 Скин: {data['skin_name']}\n"
        f"🏷 Цена: {data['skin_price']} голды\n\n"
        f"<i>Администратор проверит заявку и купит скин в игре.\n"
        f"Обычно это занимает до 24 часов.</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await state.clear()


@router.callback_query(F.data == "my_withdrawals")
async def show_my_withdrawals(callback: CallbackQuery):
    """Показать заявки пользователя"""
    user_id = callback.from_user.id

    # Получаем заявки пользователя из БД
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.* FROM withdrawals w
        JOIN users u ON w.user_id = u.id
        WHERE u.telegram_id = ?
        ORDER BY w.created_at DESC
        LIMIT 10
    ''', (user_id,))

    withdrawals = cursor.fetchall()
    conn.close()

    if not withdrawals:
        text = "📋 <b>Ваши заявки на вывод</b>\n\nУ вас нет заявок на вывод."
    else:
        text = "📋 <b>Ваши заявки на вывод</b>\n\n"
        for w in withdrawals:
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'rejected': '❌'
            }.get(w['status'], '❓')

            text += (
                f"{status_emoji} <b>Заявка #{w['id']}</b>\n"
                f"💰 Сумма: {w['amount']} RUB\n"
                f"🎮 Скин: {w['skin_name']}\n"
                f"🏷 Цена: {w['skin_price']} голды\n"
                f"📅 Дата: {w['created_at'][:10]}\n"
                f"📊 Статус: {w['status']}\n"
                f"────────────────────\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="profile")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
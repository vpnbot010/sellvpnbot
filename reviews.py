from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import REVIEW_CHANNEL_ID
from database.db import Database

router = Router()
db = Database()


class ReviewStates(StatesGroup):
    waiting_rating = State()
    waiting_text = State()


# Глобальные переменные
CHANNEL_CHAT_ID = None
CHANNEL_USERNAME = None


async def resolve_channel_id(bot, channel_identifier):
    """Преобразуем @username или ID в числовой chat_id"""
    global CHANNEL_CHAT_ID, CHANNEL_USERNAME

    if not channel_identifier or not channel_identifier.strip():
        return None

    channel_id = channel_identifier.strip()

    try:
        chat = await bot.get_chat(channel_id)
        CHANNEL_CHAT_ID = chat.id
        CHANNEL_USERNAME = chat.username

        # Проверяем права бота
        chat_member = await bot.get_chat_member(chat.id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            print("❌ Бот не администратор канала")
            return None

        return chat.id

    except Exception as e:
        print(f"❌ Ошибка получения информации о канале: {e}")
        return None


@router.message(F.text == "⭐ Отзывы")
@router.callback_query(F.data == "reviews")
async def show_reviews(event: Message | CallbackQuery):
    """Показываем меню отзывов"""
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
        bot = event.bot
    else:
        message = event
        user_id = event.from_user.id
        bot = event.bot

    # Проверяем, оставлял ли пользователь отзыв
    has_reviewed = db.has_user_reviewed(user_id)

    # Создаем клавиатуру
    keyboard_buttons = []

    if not has_reviewed:
        # Пользователь еще не оставлял отзыв
        keyboard_buttons.append([
            InlineKeyboardButton(text="💬 Оставить отзыв", callback_data="leave_review")
        ])
    else:
        # Пользователь уже оставлял отзыв
        review = db.get_user_review(user_id)
        if review:
            rating = review.get('rating', 5)
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⭐ Ваш отзыв ({rating}/5)", callback_data="view_my_review")
            ])

    # Если указан канал, добавляем кнопку
    if REVIEW_CHANNEL_ID and REVIEW_CHANNEL_ID.strip():
        channel_id = REVIEW_CHANNEL_ID.strip()

        # Формируем ссылку
        if channel_id.startswith('@'):
            channel_link = f"https://t.me/{channel_id[1:]}"
        elif channel_id.startswith('-100'):
            channel_link = f"https://t.me/c/{channel_id[4:]}"
        elif 't.me/' in channel_id:
            if not channel_id.startswith('http'):
                channel_link = f"https://{channel_id}"
            else:
                channel_link = channel_id
        else:
            channel_link = f"https://t.me/{channel_id}"

        keyboard_buttons[0].append(
            InlineKeyboardButton(text="📊 Наш канал", url=channel_link)
        )

    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu")])

    # Проверяем доступность канала для отправки сообщений
    global CHANNEL_CHAT_ID
    if REVIEW_CHANNEL_ID and not CHANNEL_CHAT_ID:
        CHANNEL_CHAT_ID = await resolve_channel_id(bot, REVIEW_CHANNEL_ID)

    # Формируем текст
    if has_reviewed:
        welcome_text = (
            "⭐ <b>Отзывы наших клиентов</b>\n\n"
            "Вы уже оставляли отзыв о нашем магазине.\n\n"
            "<i>Спасибо за ваше мнение!</i>"
        )
    else:
        welcome_text = (
            "⭐ <b>Отзывы наших клиентов</b>\n\n"
            "Оставьте отзыв о нашем магазине!\n\n"
            "<i>Каждый отзыв помогает нам стать лучше</i>"
        )

    await message.answer(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "leave_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Начинаем процесс оставления отзыва"""
    user_id = callback.from_user.id

    # Проверяем, не оставлял ли уже отзыв
    if db.has_user_reviewed(user_id):
        await callback.answer("❌ Вы уже оставляли отзыв", show_alert=True)
        return

    await state.set_state(ReviewStates.waiting_rating)

    await callback.message.edit_text(
        "⭐ <b>Оцените наш магазин</b>\n\n"
        "Выберите количество звезд от 1 до 5:\n\n"
        "<i>Используйте /cancel для отмены</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⭐", callback_data="rate_1"),
                    InlineKeyboardButton(text="⭐⭐", callback_data="rate_2"),
                    InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate_3")
                ],
                [
                    InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rate_4"),
                    InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rate_5")
                ],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="menu")]
            ]
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "view_my_review")
async def view_my_review(callback: CallbackQuery):
    """Показываем отзыв пользователя"""
    user_id = callback.from_user.id
    review = db.get_user_review(user_id)

    if not review:
        await callback.answer("❌ Отзыв не найден")
        return

    rating = review.get('rating', 5)
    text = review.get('text', '')
    date = review.get('created_at', '')

    await callback.message.edit_text(
        f"⭐ <b>Ваш отзыв</b>\n\n"
        f"Оценка: {'⭐' * rating}\n"
        f"Дата: {date[:10] if date else 'Неизвестно'}\n\n"
        f"💬 <b>Текст отзыва:</b>\n{text}\n\n"
        f"<i>Спасибо за ваше мнение!</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Наш канал",
                                      url=f"https://t.me/{REVIEW_CHANNEL_ID[1:]}" if REVIEW_CHANNEL_ID and REVIEW_CHANNEL_ID.startswith(
                                          '@') else "#")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="reviews")]
            ]
        ),
        parse_mode="HTML"
    )


@router.callback_query(ReviewStates.waiting_rating, F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем выбор рейтинга"""
    user_id = callback.from_user.id

    # Двойная проверка
    if db.has_user_reviewed(user_id):
        await callback.answer("❌ Вы уже оставляли отзыв", show_alert=True)
        await state.clear()
        await show_reviews(callback)
        return

    rating = int(callback.data.split("_")[1])

    if rating < 1 or rating > 5:
        await callback.answer("❌ Некорректная оценка")
        return

    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_text)

    await callback.message.edit_text(
        f"✅ Вы поставили оценку: {'⭐' * rating}\n\n"
        f"Теперь напишите ваш отзыв:\n"
        f"• Что понравилось?\n"
        f"• Что можно улучшить?\n\n"
        f"<i>Отзыв должен содержать хотя бы 10 символов</i>\n"
        f"<i>Используйте /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.message(ReviewStates.waiting_text)
async def process_review_text(message: Message, state: FSMContext):
    """Обрабатываем текст отзыва"""
    user_id = message.from_user.id

    # Финальная проверка
    if db.has_user_reviewed(user_id):
        await message.answer("❌ Вы уже оставляли отзыв")
        await state.clear()
        return

    if message.text == "/cancel":
        await message.answer("❌ Создание отзыва отменено")
        await state.clear()
        return

    text = message.text.strip()

    if len(text) < 10:
        await message.answer("❌ Отзыв слишком короткий. Напишите хотя бы 10 символов")
        return

    data = await state.get_data()
    rating = data.get('rating', 5)

    # Сохраняем отзыв в БД
    success = db.add_review(user_id, rating, text)

    if not success:
        await message.answer("❌ Ошибка при сохранении отзыва")
        await state.clear()
        return

    # НЕ начисляем бонус за отзыв (убрано db.update_balance)

    # Пытаемся опубликовать в канале если он доступен
    published_to_channel = False

    global CHANNEL_CHAT_ID

    if CHANNEL_CHAT_ID:
        try:
            review_text = (
                f"⭐ <b>Новый отзыв!</b>\n\n"
                f"Оценка: {'⭐' * rating}\n"
                f"👤 Пользователь: @{message.from_user.username or 'Аноним'}\n"
                f"💬 Отзыв:\n{text}\n\n"
                f"#отзыв"
            )

            await message.bot.send_message(
                chat_id=CHANNEL_CHAT_ID,
                text=review_text,
                parse_mode="HTML"
            )
            published_to_channel = True

        except Exception as e:
            print(f"❌ Ошибка публикации отзыва в канал: {e}")
            published_to_channel = False

    # Создаем клавиатуру
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Кейсы", callback_data="cases")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ]
    )

    # Формируем ответ (без упоминания бонуса)
    if published_to_channel:
        response_text = (
            f"✅ <b>Спасибо за отзыв!</b>\n\n"
            f"<i>Ваш отзыв опубликован в нашем канале!</i>"
        )
    else:
        response_text = (
            f"✅ <b>Спасибо за отзыв!</b>\n\n"
            f"<i>Ваш отзыв сохранен!</i>"
        )

    await message.answer(
        response_text,
        reply_markup=kb,
        parse_mode="HTML"
    )

    await state.clear()


@router.message(Command("myreview"))
async def cmd_myreview(message: Message):
    """Команда для просмотра своего отзыва"""
    user_id = message.from_user.id
    review = db.get_user_review(user_id)

    if not review:
        await message.answer("❌ Вы еще не оставляли отзыв")
        return

    rating = review.get('rating', 5)
    text = review.get('text', '')
    date = review.get('created_at', '')

    await message.answer(
        f"⭐ <b>Ваш отзыв</b>\n\n"
        f"Оценка: {'⭐' * rating}\n"
        f"Дата: {date[:10] if date else 'Неизвестно'}\n\n"
        f"💬 <b>Текст отзыва:</b>\n{text}\n\n"
        f"<i>Спасибо за ваше мнение!</i>",
        parse_mode="HTML"
    )
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from database.db import Database

router = Router()
db = Database()


class PromoStates(StatesGroup):
    waiting_promo = State()


@router.message(F.text == "🎟 Промокод")
@router.callback_query(F.data == "promo")
async def promo_menu(event: Message | CallbackQuery, state: FSMContext):
    """Меню промокодов"""
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id

    # Проверяем, использовал ли пользователь ЛЮБОЙ промокод
    has_used_any_promo = db.has_user_used_any_promo(user_id)

    if has_used_any_promo:
        text = (
            "🎟 <b>Промокоды</b>\n\n"
            "Вы уже использовали промокод.\n\n"
            "<i>Каждый пользователь может использовать только один промокод</i>"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
            ]
        )
    else:
        text = (
            "🎟 <b>Промокоды</b>\n\n"
            "Введите промокод для получения скидки 20% на покупку кейсов.\n\n"
            "<i>Каждый пользователь может использовать только один промокод</i>"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💎 Ввести промокод", callback_data="enter_promo")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
            ]
        )

    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    """Ввод промокода"""
    user_id = callback.from_user.id

    # Проверяем, не использовал ли уже ЛЮБОЙ промокод
    if db.has_user_used_any_promo(user_id):
        await callback.answer("❌ Вы уже использовали промокод", show_alert=True)
        return

    await state.set_state(PromoStates.waiting_promo)

    await callback.message.edit_text(
        "🎟 <b>Введите промокод:</b>\n\n"
        "Промокод дает скидку 20% на покупку кейсов\n\n"
        "<i>Используйте /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.message(PromoStates.waiting_promo)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка введенного промокода"""
    user_id = message.from_user.id

    if message.text == "/cancel":
        await message.answer("❌ Ввод промокода отменен")
        await state.clear()
        return

    promo_code = message.text.strip().upper()

    # Проверяем, не использовал ли уже ЛЮБОЙ промокод
    if db.has_user_used_any_promo(user_id):
        await message.answer("❌ Вы уже использовали промокод")
        await state.clear()
        return

    # Проверяем промокод
    promo = db.check_promocode(promo_code)

    if not promo:
        await message.answer(
            "❌ <b>Промокод не найден или неактивен</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать другой", callback_data="enter_promo")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="promo")]
                ]
            ),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Проверяем, использовал ли уже этот промокод
    if db.has_user_used_this_promo(user_id, promo_code):
        await message.answer("❌ Вы уже использовали этот промокод")
        await state.clear()
        return

    # Помечаем промокод как использованный
    success = db.use_promocode(promo_code, user_id)

    if not success:
        await message.answer("❌ Ошибка применения промокода")
        await state.clear()
        return

    discount = promo.get('discount', 0.2) * 100

    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"🎟 Код: <code>{promo_code}</code>\n"
        f"🎁 Скидка: <b>{discount}%</b>\n\n"
        f"<i>Скидка будет применена при следующей покупке кейса</i>\n"
        f"<i>Каждый пользователь может использовать только один промокод</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Купить кейсы", callback_data="cases")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
            ]
        ),
        parse_mode="HTML"
    )

    await state.clear()


@router.message(Command("promo"))
async def cmd_promo(message: Message):
    """Команда для промокодов"""
    await promo_menu(message, None)

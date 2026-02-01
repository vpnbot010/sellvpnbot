from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "❌ Нет активных действий для отмены",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]]
            )
        )
        return

    await state.clear()
    await message.answer(
        "✅ Действие отменено",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]]
        )
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь по командам"""
    help_text = (
        "⚔ <b>SharpDrop - Помощь</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Главное меню\n"
        "/menu - Главное меню\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущее действие\n\n"
        "<b>Основные разделы:</b>\n"
        "🎁 Кейсы - Купить кейсы\n"
        "🎒 Инвентарь - Ваши кейсы и предметы\n"
        "👤 Профиль - Ваш баланс и информация\n"
        "💰 Вывод - Вывести средства\n"
        "⭐ Отзывы - Оставить отзыв\n"
        "🎟 Промокод - Ввести промокод\n\n"
        "<b>Поддержка:</b>\n"
        "По всем вопросам обращайтесь к администратору"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("menu"))
@router.callback_query(F.data == "menu")
async def menu_handler(event: Message | CallbackQuery):
    """Главное меню"""
    from handlers.start import WELCOME_TEXT
    from keyboards.buttons import main_menu

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")
    else:
        await event.answer(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Показать баланс"""
    from handlers.profile import show_profile
    await show_profile(message)

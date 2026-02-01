from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from database.db import Database
from keyboards.buttons import main_menu

router = Router()
db = Database()

WELCOME_TEXT = """
⚔ <b>SharpDrop - Кейсы Standoff 2</b>

🛠 STANDOFF SHOP — Магазин, созданный игроками для игроков!

Что у нас есть:
📦 Уникальные кейсы: От «Бюджетного» до «Королевского»
📈 Drop Rate: Мы открыто говорим — у нас падает круче!
💸 Экономика: Продавай выбитые скины боту и крути снова
🛡 Гарантии: Работаем через официальное API и проверенные методы
🎁 Ежедневные бонусы: Заходи каждый день и забирай халявную голду!

🚀 Переходи и испытай удачу!
"""


@router.message(CommandStart())
async def cmd_start(message: Message):
    db.add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

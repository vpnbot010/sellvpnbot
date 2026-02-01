from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import CASES
from keyboards.buttons import cases_menu, case_detail_menu
from database.db import Database

router = Router()
db = Database()


@router.message(F.text == "🎁 Кейсы")
@router.message(Command("cases"))
async def show_cases(message: Message):
    await message.answer(
        "🎮 <b>Выберите кейс:</b>\n\n",
        reply_markup=cases_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cases")
async def show_cases_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>Выберите кейс:</b>\n\n",
        reply_markup=cases_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("case_"))
async def case_detail(callback: CallbackQuery):
    case_id = int(callback.data.split("_")[1])
    case = CASES.get(case_id)

    if not case:
        await callback.answer("Кейс не найден")
        return

    # Формируем список предметов
    items_text = ""
    for i, item in enumerate(case["items"]):
        items_text += f"{item['emoji']} {item['chance']}% — {item['name']}\n | {item['rarity']} | ~ {item['price']}G\n"
        if i < len(case["items"]) - 1:  # Не добавляем разделитель после последнего элемента
            items_text += "===========================\n"

    await callback.message.edit_text(
        f"<b>{case['name']}</b>\n\n"
        f"💰 Цена: <b>{case['price']}₽</b> или <b>{case['stars']} ⭐</b>\n\n"
        f"📦 <b>Содержимое:</b>\n{items_text}\n"
        f"Выберите действие:",
        reply_markup=case_detail_menu(case_id),
        parse_mode="HTML"
    )

import random
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import CASES, CARD_NUMBER, CARD_HOLDER, BANK, ADMIN_IDS, MIN_STARS_PURCHASE
from keyboards.buttons import payment_methods_menu, confirm_payment_menu
from database.db import Database

logger = logging.getLogger(__name__)

router = Router()
db = Database()


class PaymentStates(StatesGroup):
    waiting_payment = State()
    waiting_promo = State()


@router.callback_query(F.data.startswith("buy_"))
async def buy_case_start(callback: CallbackQuery, state: FSMContext):
    case_id = int(callback.data.split("_")[1])
    case = CASES.get(case_id)

    if not case:
        await callback.answer("Кейс не найден")
        return

    user_id = callback.from_user.id

    # Проверяем, использовал ли пользователь ЛЮБОЙ промокод
    has_used_promo = db.has_user_used_any_promo(user_id)

    # Сбрасываем предыдущие данные
    await state.clear()
    await state.update_data(
        case_id=case_id,
        price=case["price"],
        stars=case["stars"],
        original_price=case["price"],
        has_used_promo=has_used_promo
    )

    if has_used_promo:
        text = (
            f"💰 <b>Покупка кейса:</b> {case['name']}\n"
            f"📦 Стоимость: <b>{case['price']}₽</b> или <b>{case['stars']} ⭐</b>\n"
            f"<i>Вы уже использовали промокод</i>\n"
            f"Выберите способ оплаты:"
        )
    else:
        text = (
            f"💰 <b>Покупка кейса:</b> {case['name']}\n"
            f"📦 Стоимость: <b>{case['price']}₽</b> или <b>{case['stars']} ⭐</b>\n"
            f"💎 Со скидкой: <b>{case['price'] * 0.8:.0f}₽</b> (~{int(case['stars'] * 0.8)} ⭐)\n\n"
            f"<i>Можно применить промокод для скидки 20%</i>\n"
            f"Выберите способ оплаты:"
        )

    await callback.message.edit_text(
        text,
        reply_markup=payment_methods_menu(case_id, has_used_promo),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery, state: FSMContext):
    case_id = int(callback.data.split("_")[2])
    case = CASES.get(case_id)

    if not case:
        await callback.answer("Кейс не найден")
        return

    data = await state.get_data()
    price = data.get('price', case["price"])

    # Создаем заказ
    order_id = db.create_order(
        telegram_id=callback.from_user.id,
        case_id=case_id,
        amount=price,
        payment_method="card"
    )

    if not order_id:
        await callback.answer("Ошибка создания заказа")
        return

    await state.update_data(order_id=order_id)

    # Формируем текст
    payment_text = (
        f"💳 <b>Оплата картой</b>\n\n"
        f"Кейс: {case['name']}\n"
        f"Сумма: <b>{price}₽</b>\n\n"
        f"<b>Реквизиты:</b>\n"
        f"Номер карты: <code>{CARD_NUMBER}</code>\n"
        f"Получатель: {CARD_HOLDER}\n"
        f"Банк: {BANK}\n\n"
        f"После оплаты нажмите кнопку ниже.\n"
        f"<i>Заказ будет обработан в течение 5-15 минут</i>"
    )

    await callback.message.edit_text(
        payment_text,
        reply_markup=confirm_payment_menu(order_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery):
    case_id = int(callback.data.split("_")[2])
    case = CASES.get(case_id)

    if not case:
        await callback.answer("❌ Кейс не найден")
        return

    # Берем количество звезд из конфига
    stars_needed = case["stars"]

    if stars_needed < MIN_STARS_PURCHASE:
        await callback.answer(f"❌ Минимальная покупка: {MIN_STARS_PURCHASE} звёзд")
        return

    # Создаем инвойс для оплаты звездами
    try:
        # Для Telegram Stars используем специальный формат
        invoice = await callback.bot.create_invoice_link(
            title=f"Кейс: {case['name']}",
            description=f"Покупка кейса {case['name']} за {stars_needed} звезд.",
            payload=f"case_{case_id}_{callback.from_user.id}",
            currency="XTR",  # Telegram Stars
            prices=[{"label": "Stars", "amount": stars_needed}],
        )

        # Создаем заказ
        order_id = db.create_order(
            telegram_id=callback.from_user.id,
            case_id=case_id,
            amount=stars_needed,
            payment_method="stars"
        )

        if not order_id:
            await callback.answer("❌ Ошибка создания заказа")
            return

        await callback.message.edit_text(
            f"⭐ <b>Оплата звездами</b>\n\n"
            f"Кейс: {case['name']}\n"
            f"Стоимость: <b>{stars_needed} ⭐</b>\n"
            f"<i>Для оплаты нажмите на кнопку ниже:</i>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"💫 Оплатить {stars_needed} ⭐", url=invoice)],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data=f"case_{case_id}")]
                ]
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка создания инвойса: {e}")
        await callback.answer("❌ Ошибка создания платежа. Попробуйте позже.")


@router.callback_query(F.data.startswith("apply_promo_"))
async def apply_promo_to_purchase(callback: CallbackQuery, state: FSMContext):
    """Применение промокода к покупке"""
    case_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    case = CASES.get(case_id)
    if not case:
        await callback.answer("❌ Кейс не найден")
        return

    # Проверяем, не использовал ли уже промокод
    if db.has_user_used_any_promo(user_id):
        await callback.answer("❌ Вы уже использовали промокод", show_alert=True)
        return

    await state.set_state(PaymentStates.waiting_promo)
    await state.update_data(
        case_id=case_id,
        original_price=case["price"],
        original_stars=case["stars"]
    )

    await callback.message.edit_text(
        "🎟 <b>Введите промокод для скидки 20%</b>\n\n"
        f"Кейс: {case['name']}\n"
        f"Цена без скидки: {case['price']}₽ ({case['stars']} ⭐)\n"
        f"Цена со скидкой: {case['price'] * 0.8:.0f}₽ (~{int(case['stars'] * 0.8)} ⭐)\n\n"
        "<i>Напишите /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("paid_"))
async def confirm_payment(callback: CallbackQuery):
    """Пользователь подтверждает оплату картой"""
    try:
        order_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка в данных заказа")
        return

    # Получаем заказ из базы по ID
    order = db.get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден")
        logger.error(f"Заказ {order_id} не найден для пользователя {callback.from_user.id}")
        return

    # Проверяем, принадлежит ли заказ этому пользователю
    if order['telegram_id'] != callback.from_user.id:
        await callback.answer("❌ Этот заказ не принадлежит вам")
        return

    # Проверяем, что заказ еще не обработан
    if order['status'] != 'pending':
        await callback.answer(f"❌ Этот заказ уже обработан (статус: {order['status']})")
        return

    # Обновляем статус заказа на "waiting_confirmation"
    db.update_order_status(order_id, "waiting_confirmation")

    await callback.message.edit_text(
        "✅ <b>Спасибо! Ваша оплата принята</b>\n\n"
        "Администратор проверит оплату в течение 5-15 минут\n"
        "Как только оплата будет подтверждена, кейс появится в вашем инвентаре\n\n"
        "⏳ Ожидайте уведомления",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu")
            ]]
        ),
        parse_mode="HTML"
    )

    # Уведомляем админа С КНОПКОЙ
    from config import CASES, ADMIN_IDS
    case = CASES.get(order['case_id'], {})

    kb_admin = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
            ]
        ]
    )

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"💰 <b>Новый заказ ожидает подтверждения</b>\n\n"
                f"Заказ #{order_id}\n"
                f"👤 Пользователь: @{callback.from_user.username or 'без username'}\n"
                f"ID: {callback.from_user.id}\n"
                f"🎁 Кейс: {case.get('name', 'Неизвестно')}\n"
                f"💰 Сумма: {order['amount']}₽\n"
                f"💳 Способ оплаты: {order.get('payment_method', 'Карта')}\n\n"
                f"<b>Проверьте поступление на карту</b>",
                reply_markup=kb_admin,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка уведомления админа: {e}")

# ВАЖНО: ОСТАВИТЬ ТОЛЬКО ОДИН ОБРАБОТЧИК!
@router.message(PaymentStates.waiting_promo)
async def process_promo_for_purchase(message: Message, state: FSMContext):
    """Обработка промокода для покупки"""
    user_id = message.from_user.id

    if message.text == "/cancel":
        await message.answer("❌ Применение промокода отменено")
        await state.clear()
        return

    promo_code = message.text.strip().upper()
    data = await state.get_data()
    case_id = data.get('case_id')
    original_price = data.get('original_price')
    original_stars = data.get('original_stars')

    case = CASES.get(case_id)
    if not case:
        await message.answer("❌ Кейс не найден")
        await state.clear()
        return

    # Проверяем, не использовал ли уже промокод
    if db.has_user_used_any_promo(user_id):
        await message.answer("❌ Вы уже использовали промокод")
        await state.clear()
        return

    # Проверяем промокод
    promo = db.check_promocode(promo_code)

    if not promo:
        await message.answer(
            "❌ <b>Промокод не найден или неактивен</b>\n\n"
            f"Цена без скидки: {original_price}₽ ({original_stars} ⭐)",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🔄 Попробовать другой", callback_data=f"apply_promo_{case_id}"),
                        InlineKeyboardButton(text="🚀 Без скидки", callback_data=f"pay_card_{case_id}")
                    ]
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

    # Применяем скидку
    discount = promo.get('discount', 0.2)
    final_price = original_price * (1 - discount)
    final_stars = int(original_stars * (1 - discount))

    # Помечаем промокод как использованный
    success = db.use_promocode(promo_code, user_id)

    if not success:
        await message.answer("❌ Ошибка применения промокода")
        await state.clear()
        return

    await state.update_data(
        price=final_price,
        stars=final_stars,
        promo_code=promo_code,
        discount=discount,
        final_price=final_price
    )

    await message.answer(
        f"✅ <b>Промокод применен!</b>\n\n"
        f"🎟 Код: <code>{promo_code}</code>\n"
        f"🎁 Скидка: {discount * 100}%\n"
        f"💰 Итоговая цена: <b>{final_price:.0f}₽</b> (~{final_stars} ⭐)\n\n"
        f"Кейс: {case['name']}\n"
        f"Получите: <b>{case['price_gold']} голды</b>\n\n"
        f"Выберите способ оплаты:",
        reply_markup=payment_methods_menu(case_id, has_used_promo=True),
        parse_mode="HTML"
    )

    await state.clear()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Проверяем платеж
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment

    # Получаем данные из payload
    payload = payment.invoice_payload
    if payload.startswith("case_"):
        parts = payload.split("_")
        if len(parts) >= 3:
            case_id = int(parts[1])
            user_id = int(parts[2])

            # Проверяем, что платеж отправил тот же пользователь
            if message.from_user.id != user_id:
                await message.answer("❌ Ошибка: платеж от другого пользователя")
                return

            case = CASES.get(case_id)
            if case:
                # Создаем заказ со статусом completed
                order_id = db.create_order(
                    telegram_id=user_id,
                    case_id=case_id,
                    amount=payment.total_amount / 100,
                    payment_method="stars"
                )

                if order_id:
                    # Обновляем статус заказа
                    db.update_order_status(order_id, "completed")

                    # Сохраняем кейс в инвентарь
                    case_item = {
                        "name": case['name'],
                        "rarity": "Case",
                        "price": 0,
                    }

                    db.add_to_inventory(user_id, case_id, case_item)

                    await message.answer(
                        f"✅ <b>Оплата успешно принята!</b>\n\n"
                        f"🎁 Кейс: {case['name']}\n"
                        f"🛒 Теперь кейс доступен в вашем инвентаре!\n\n"
                        f"Перейдите в 🎒 Инвентарь чтобы открыть кейс",
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="🎒 Открыть инвентарь", callback_data="inventory")],
                                [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
                                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
                            ]
                        ),
                        parse_mode="HTML"
                    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="🎁 Кейсы", callback_data="cases")
    )
    kb.row(
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews")
    )
    kb.row(
        InlineKeyboardButton(text="🎟 Промокод", callback_data="promo"),
        InlineKeyboardButton(text="💰 Вывод", callback_data="withdraw")
    )
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))
    return kb.as_markup()


def cases_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    from config import CASES

    for case_id, case_data in CASES.items():
        kb.row(
            InlineKeyboardButton(
                text=f"{case_data['name']} - {case_data['price']}₽",
                callback_data=f"case_{case_id}"
            )
        )

    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))
    return kb.as_markup()


def case_detail_menu(case_id: int) -> InlineKeyboardMarkup:
    """Меню деталей кейса"""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_{case_id}"),
        InlineKeyboardButton(text="🎟 Применить промокод", callback_data=f"apply_promo_{case_id}")
    )
    kb.row(InlineKeyboardButton(text="◀️ Назад к кейсам", callback_data="cases"))
    return kb.as_markup()


def payment_methods_menu(case_id: int, has_used_promo: bool = False):
    """Клавиатура методов оплаты"""
    kb = InlineKeyboardBuilder()

    kb.row(
        InlineKeyboardButton(text="💳 Карта", callback_data=f"pay_card_{case_id}"),
        InlineKeyboardButton(text="⭐ Звёзды", callback_data=f"pay_stars_{case_id}")
    )

    if not has_used_promo:
        kb.row(InlineKeyboardButton(text="🎟 Применить промокод", callback_data=f"apply_promo_{case_id}"))

    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"case_{case_id}"))

    return kb.as_markup()


def confirm_payment_menu(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{order_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cases")
    )
    return kb.as_markup()


def admin_order_menu(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Меню заказа для админа"""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    )
    kb.row(
        InlineKeyboardButton(text="👤 Профиль", url=f"tg://user?id={user_id}"),
        InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")
    )
    return kb.as_markup()


def admin_withdrawal_menu(withdrawal_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Меню вывода для админа"""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Выплачено", callback_data=f"admin_withdraw_confirm_{withdrawal_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_withdraw_reject_{withdrawal_id}")
    )
    kb.row(
        InlineKeyboardButton(text="👤 Профиль", url=f"tg://user?id={user_id}"),
        InlineKeyboardButton(text="📋 К выводам", callback_data="admin_withdrawals")
    )
    return kb.as_markup()


def admin_panel_menu() -> InlineKeyboardMarkup:
    """Меню админ-панели"""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 К промокодам", callback_data="admin_promocodes"),
        InlineKeyboardButton(text="📋 К заказам", callback_data="admin_orders")
    )
    kb.row(
        InlineKeyboardButton(text="📤 К выводам", callback_data="admin_withdrawals"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    return kb.as_markup()


def inventory_menu(items: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for item in items:
        kb.row(
            InlineKeyboardButton(
                text=f"{item['item_name']} - {item['item_price']}G",
                callback_data=f"open_{item['id']}"
            )
        )

    if not items:
        kb.row(InlineKeyboardButton(text="🎒 Инвентарь пуст", callback_data="none"))

    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))
    return kb.as_markup()


def item_action_menu(item_id: int, item_price: float) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="💰 Продать", callback_data=f"sell_{item_id}"),
        InlineKeyboardButton(text="💾 Оставить", callback_data="inventory")
    )
    kb.row(InlineKeyboardButton(text="◀️ В инвентарь", callback_data="inventory"))
    return kb.as_markup()


def review_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"rate_{i}")
    kb.row(InlineKeyboardButton(text="◀️ Пропустить", callback_data="menu"))
    return kb.as_markup()


def yes_no_menu(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_callback)
    )
    return kb.as_markup()

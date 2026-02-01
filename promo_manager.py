import random
import string
from database.db import Database

db = Database()


def generate_promo_code(length=8):
    """Генерация промокода"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def apply_promo_code(user_id: int, code: str, purchase_amount: float) -> dict:
    """Применение промокода"""
    promo = db.check_promocode(code)

    if not promo:
        return {"success": False, "message": "Промокод не найден или неактивен"}

    # Проверяем использовал ли уже пользователь этот промокод
    import json
    used_by = json.loads(promo.get('used_by', '[]'))

    if str(user_id) in used_by:
        return {"success": False, "message": "Вы уже использовали этот промокод"}

    # Применяем скидку
    discount = promo.get('discount', 0.2)  # 20% по умолчанию
    final_amount = purchase_amount * (1 - discount)
    saved_amount = purchase_amount - final_amount

    # Помечаем промокод как использованный
    db.use_promocode(code, user_id)

    return {
        "success": True,
        "discount": discount,
        "final_amount": final_amount,
        "saved_amount": saved_amount,
        "code": code
    }
import sqlite3
import json
import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import CASES


class Database:
    def __init__(self, db_path: str = None):
        # На Render используем абсолютный путь
        if db_path is None:
            # Проверяем, есть ли переменная окружения для пути к БД
            if "RENDER" in os.environ:
                # На Render используем /tmp для временных файлов
                db_path = "/tmp/database.db"
            else:
                db_path = "database.db"

        self.db_path = db_path
        print(f"Используется база данных: {self.db_path}")
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Создаем все таблицы если их нет"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0.0,
                reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица инвентаря
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                item_rarity TEXT NOT NULL,
                item_price REAL NOT NULL,
                is_opened BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Таблица выводов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                game_nickname TEXT NOT NULL,
                skin_name TEXT NOT NULL,
                skin_price REAL NOT NULL,
                screenshot_url TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Таблица промокодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount REAL DEFAULT 0.2,
                used_by TEXT DEFAULT '[]',
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # Таблица отзывов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()

    def add_user(self, telegram_id: int, username: str = None, full_name: str = None):
        """Добавляем пользователя если его нет"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
                (telegram_id, username, full_name)
            )
            conn.commit()
        except Exception as e:
            print(f"Ошибка добавления пользователя: {e}")
        finally:
            conn.close()

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Получаем пользователя по telegram_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def update_balance(self, telegram_id: int, amount: float):
        """Обновляем баланс пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id)
        )
        conn.commit()
        conn.close()

    # === ИНВЕНТАРЬ ===

    def get_inventory(self, telegram_id: int) -> List[Dict]:
        """Получаем весь инвентарь пользователя (и кейсы и предметы)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT i.* FROM inventory i
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY 
                CASE WHEN i.item_rarity = 'Case' THEN 0 ELSE 1 END,
                i.created_at DESC
        ''', (telegram_id,))

        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return items

    def add_to_inventory(self, telegram_id: int, case_id: int, item: Dict):
        """Добавляем предмет в инвентарь"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем user_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return False

        cursor.execute(
            '''INSERT INTO inventory 
               (user_id, case_id, item_name, item_rarity, item_price) 
               VALUES (?, ?, ?, ?, ?)''',
            (user['id'], case_id, item['name'], item['rarity'], item['price'])
        )
        conn.commit()
        conn.close()
        return True

    def mark_item_as_opened(self, item_id: int):
        """Помечаем предмет как открытый"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inventory SET is_opened = 1 WHERE id = ?",
            (item_id,)
        )
        conn.commit()
        conn.close()

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Получаем предмет по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        conn.close()
        return dict(item) if item else None

    def remove_from_inventory(self, item_id: int):
        """Удаляем предмет из инвентаря"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    # === ЗАКАЗЫ ===

    def create_order(self, telegram_id, case_id, amount, payment_method="card"):
        """Создать новый заказ"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем user_id пользователя
        cursor.execute("SELECT id, username FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return None

        user_id = user['id']
        username = user['username']

        # Вставляем заказ со статусом 'pending' - используем правильные названия колонок
        cursor.execute("""
            INSERT INTO orders (user_id, case_id, amount, payment_method, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, case_id, amount, payment_method, "pending"))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return order_id

    def update_order_status(self, order_id: int, status: str):
        """Обновляем статус заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        conn.commit()
        conn.close()

    def get_pending_orders(self) -> List[Dict]:
        """Получаем заказы ожидающие подтверждения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                o.*, 
                u.telegram_id, 
                u.username 
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.status = 'pending' OR o.status = 'waiting_confirmation'
            ORDER BY o.created_at DESC
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    # === ВЫВОДЫ ===

    def create_withdrawal(self, telegram_id: int, amount: float, game_nickname: str,
                          skin_name: str, skin_price: float, screenshot_url: str = None):
        """Создаем заявку на вывод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return None

        cursor.execute(
            '''INSERT INTO withdrawals 
               (user_id, amount, game_nickname, skin_name, skin_price, screenshot_url)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user['id'], amount, game_nickname, skin_name, skin_price, screenshot_url)
        )
        withdrawal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return withdrawal_id

    def update_withdrawal_status(self, withdrawal_id: int, status: str):
        """Обновляем статус вывода"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE withdrawals SET status = ? WHERE id = ?",
            (status, withdrawal_id)
        )
        conn.commit()
        conn.close()

    def get_pending_withdrawals(self) -> List[Dict]:
        """Получаем выводы ожидающие подтверждения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, u.telegram_id, u.username 
            FROM withdrawals w
            JOIN users u ON w.user_id = u.id
            WHERE w.status = 'pending'
            ORDER BY w.created_at DESC
        ''')
        withdrawals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return withdrawals

    # === ПРОМОКОДЫ ===

    def add_promocode(self, code: str, discount: float = 0.2):
        """Добавляем промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO promocodes (code, discount) VALUES (?, ?)",
            (code, discount)
        )
        conn.commit()
        conn.close()

    def check_promocode(self, code: str) -> Optional[Dict]:
        """Проверяем промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM promocodes WHERE code = ? AND is_active = 1",
            (code,)
        )
        promo = cursor.fetchone()
        conn.close()
        return dict(promo) if promo else None

    def use_promocode(self, code: str, telegram_id: int) -> bool:
        """Используем промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT used_by FROM promocodes WHERE code = ?", (code,))
        promo = cursor.fetchone()
        if not promo:
            conn.close()
            return False

        used_by = json.loads(promo['used_by'])
        if str(telegram_id) in used_by:
            conn.close()
            return False

        used_by.append(str(telegram_id))
        cursor.execute(
            "UPDATE promocodes SET used_by = ? WHERE code = ?",
            (json.dumps(used_by), code)
        )
        conn.commit()
        conn.close()
        return True

    # === ОТЗЫВЫ ===

    def add_review(self, telegram_id: int, rating: int, text: str):
        """Добавляем отзыв"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return False

        cursor.execute(
            "INSERT INTO reviews (user_id, rating, text) VALUES (?, ?, ?)",
            (user['id'], rating, text)
        )
        conn.commit()
        conn.close()
        return True

    def get_all_reviews(self, limit: int = 10) -> List[Dict]:
        """Получаем все отзывы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.username 
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
            LIMIT ?
        ''', (limit,))
        reviews = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reviews

    def get_user_cases(self, telegram_id: int) -> List[Dict]:
        """Получаем кейсы пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT i.* FROM inventory i
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_id = ? AND i.item_rarity = 'Case'
            ORDER BY i.created_at DESC
        ''', (telegram_id,))

        cases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cases

    def get_user_items(self, telegram_id: int) -> List[Dict]:
        """Получаем предметы пользователя (не кейсы)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT i.* FROM inventory i
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_id = ? AND i.item_rarity != 'Case'
            ORDER BY i.created_at DESC
        ''', (telegram_id,))

        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return items

    def open_case(self, inventory_id: int, telegram_id: int) -> Dict:
        """Открываем кейс и получаем случайный предмет"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем информацию о кейсе
        cursor.execute("SELECT case_id FROM inventory WHERE id = ?", (inventory_id,))
        case_record = cursor.fetchone()
        if not case_record:
            conn.close()
            return None

        case_id = case_record['case_id']

        # Импортируем CASES здесь чтобы избежать циклического импорта
        from config import CASES
        case = CASES.get(case_id)
        if not case:
            conn.close()
            return None

        # Взвешенный случайный выбор предмета
        import random
        items = case["items"]
        total = sum(item["chance"] for item in items)
        r = random.uniform(0, total)
        upto = 0
        won_item = None
        for item in items:
            if upto + item["chance"] >= r:
                won_item = item.copy()  # Копируем словач чтобы не менять оригинал
                break
            upto += item["chance"]

        if not won_item:
            conn.close()
            return None

        # Удаляем кейс из инвентаря
        cursor.execute("DELETE FROM inventory WHERE id = ?", (inventory_id,))

        # Добавляем выигранный предмет
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()

        if user and won_item:
            cursor.execute(
                '''INSERT INTO inventory 
                   (user_id, case_id, item_name, item_rarity, item_price) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user['id'], case_id, won_item['name'], won_item['rarity'], won_item['price'])
            )

        conn.commit()
        conn.close()

        return won_item


    def get_pending_orders(self) -> List[Dict]:
        """Получаем заказы ожидающие подтверждения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, u.telegram_id, u.username 
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.status = 'waiting_confirmation'
            ORDER BY o.created_at DESC
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def add_to_inventory(self, telegram_id: int, case_id: int, item: Dict):
        """Добавляем предмет в инвентарь"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем user_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return False

        # Добавляем в инвентарь
        cursor.execute(
            '''INSERT INTO inventory 
               (user_id, case_id, item_name, item_rarity, item_price) 
               VALUES (?, ?, ?, ?, ?)''',
            (user['id'], case_id, item['name'], item['rarity'], item['price'])
        )
        conn.commit()
        conn.close()
        return True

    def has_case_in_inventory(self, telegram_id: int, case_id: int) -> bool:
        """Проверяем, есть ли кейс в инвентаре"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) as count FROM inventory i
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_id = ? AND i.case_id = ? AND i.item_rarity = 'Case'
        ''', (telegram_id, case_id))

        result = cursor.fetchone()
        conn.close()
        return result['count'] > 0 if result else False

    def get_user_case_count(self, telegram_id: int) -> int:
        """Получаем количество кейсов пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) as count FROM inventory i
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_id = ? AND i.item_rarity = 'Case'
        ''', (telegram_id,))

        result = cursor.fetchone()
        conn.close()
        return result['count'] if result else 0

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Получаем предмет по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        conn.close()
        return dict(item) if item else None

    def has_user_reviewed(self, telegram_id: int) -> bool:
        """Проверяем, оставлял ли пользователь отзыв"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) as count FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE u.telegram_id = ?
        ''', (telegram_id,))

        result = cursor.fetchone()
        conn.close()
        return result['count'] > 0 if result else False

    def get_user_review(self, telegram_id: int) -> Optional[Dict]:
        """Получаем отзыв пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT r.* FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY r.created_at DESC
            LIMIT 1
        ''', (telegram_id,))

        review = cursor.fetchone()
        conn.close()
        return dict(review) if review else None

    def has_user_used_any_promo(self, telegram_id: int) -> bool:
        """Проверяем, использовал ли пользователь ЛЮБОЙ промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT used_by FROM promocodes 
            WHERE is_active = 1
        ''')
        all_promos = cursor.fetchall()

        for promo in all_promos:
            import json
            used_by = json.loads(promo['used_by'])
            if str(telegram_id) in used_by:
                conn.close()
                return True

        conn.close()
        return False

    def has_user_used_this_promo(self, telegram_id: int, promo_code: str) -> bool:
        """Проверяем, использовал ли пользователь КОНКРЕТНЫЙ промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT used_by FROM promocodes 
            WHERE code = ? AND is_active = 1
        ''', (promo_code,))

        promo = cursor.fetchone()
        conn.close()

        if not promo:
            return False

        import json
        used_by = json.loads(promo['used_by'])
        return str(telegram_id) in used_by

    def get_all_promocodes(self) -> List[Dict]:
        """Получаем все промокоды"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM promocodes 
            ORDER BY is_active DESC, code ASC
        ''')

        promos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return promos

    def delete_promocode(self, code: str) -> bool:
        """Удаляем промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def toggle_promocode(self, code: str, is_active: bool) -> bool:
        """Активируем/деактивируем промокод"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE promocodes SET is_active = ? WHERE code = ?",
            (is_active, code)
        )
        updated = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return updated

    def get_withdrawal_by_id(self, withdrawal_id: int) -> Optional[Dict]:
        """Получаем вывод по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, u.telegram_id, u.username 
            FROM withdrawals w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = ?
        ''', (withdrawal_id,))
        withdrawal = cursor.fetchone()
        conn.close()
        return dict(withdrawal) if withdrawal else None

    def get_withdrawal_by_id(self, withdrawal_id: int) -> Optional[Dict]:
        """Получаем вывод по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, u.telegram_id, u.username 
            FROM withdrawals w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = ?
        ''', (withdrawal_id,))
        withdrawal = cursor.fetchone()
        conn.close()
        return dict(withdrawal) if withdrawal else None

    def get_order_by_id(self, order_id):
        """Получить заказ по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                o.*,
                u.telegram_id,
                u.username
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        ''', (order_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

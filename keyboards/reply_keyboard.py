from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_admin_reply_keyboard():
    """Reply клавиатура для администраторов"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Админ панель")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True
    )


def get_user_reply_keyboard():
    """Reply клавиатура для обычных пользователей"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True
    )

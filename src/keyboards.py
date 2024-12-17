from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup


async def start_keyboard():
    kb = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Пополнить баланс")],
        [KeyboardButton(text="Каталог"), KeyboardButton(text="Мои заказы")],
        [KeyboardButton(text="Отзыв"), KeyboardButton(text="Связаться")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    return keyboard


async def admin_keyboard():
    kb = [
        [InlineKeyboardButton(text="Добавить новую модель обуви", callback_data="add_sho")],
        [InlineKeyboardButton(text="Удалить модель обуви", callback_data="delete_sho")],
        [InlineKeyboardButton(text="Редактировать модель обуви", callback_data="edit_sho")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from src.keyboards import admin_keyboard, start_keyboard
from src.states import AdminActions

admin_router = Router(name=__name__)


@admin_router.message(Command('admin'))
async def admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        admin_message = "Выберите действие:"
        await message.answer(admin_message, reply_markup=await admin_keyboard())
    else:
        await message.answer("У вас нет доступа к данному функционалу!", reply_markup=await start_keyboard())


@admin_router.callback_query(F.data == "add_sho")
async def add_shoe_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название новой модели обуви:")
    await state.set_state(AdminActions.ADD_SHOE_NAME)


@admin_router.message(AdminActions.ADD_SHOE_NAME)
async def add_shoe_name(message: Message, state: FSMContext):
    shoe_name = message.text
    await state.update_data(shoe_name=shoe_name)
    await message.answer("Введите цену для этой модели обуви:")
    await state.set_state(AdminActions.ADD_SHOE_PRICE)


@admin_router.message(AdminActions.ADD_SHOE_PRICE)
async def add_shoe_price(message: Message, state: FSMContext, pool):
    price = message.text
    if not price.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return
    data = await state.get_data()
    shoe_name = data['shoe_name']
    price = int(price)
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO shoes (name, price) VALUES ($1, $2)",
                shoe_name, price
            )
            await message.answer(f"Модель обуви '{shoe_name}' с ценой {price} рублей добавлена в каталог.", reply_markup=await admin_keyboard())
        except Exception as e:
            print(f"Ошибка при добавлении обуви: {e}")
            await message.answer("Произошла ошибка при добавлении обуви. Попробуйте снова.", reply_markup=await admin_keyboard())
    await state.clear()


@admin_router.callback_query(F.data == "delete_sho")
async def delete_shoe_callback(callback: CallbackQuery, pool):
    async with pool.acquire() as conn:
        shoes = await conn.fetch("SELECT * FROM shoes")
        if not shoes:
            await callback.message.answer("Каталог пуст. Нечего удалять.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=shoe['name'], callback_data=f"delete_shoe_{shoe['id']}")]
            for shoe in shoes
        ])
        await callback.message.answer("Выберите модель обуви для удаления:", reply_markup=keyboard)


@admin_router.callback_query(F.data.startswith("delete_shoe_"))
async def confirm_delete_shoe_callback(callback: CallbackQuery, pool):
    shoe_id = int(callback.data.split("_")[2])
    async with pool.acquire() as conn:
        try:
            await conn.execute("DELETE FROM shoes WHERE id = $1", shoe_id)
            await callback.message.answer("Модель обуви удалена из каталога.",reply_markup=await admin_keyboard())
        except Exception as e:
            print(f"Ошибка при удалении обуви: {e}")
            await callback.message.answer("Произошла ошибка при удалении обуви.", reply_markup=await admin_keyboard())


@admin_router.callback_query(F.data == "edit_sho")
async def edit_shoe_callback(callback: CallbackQuery, pool):
    async with pool.acquire() as conn:
        shoes = await conn.fetch("SELECT * FROM shoes")
        if not shoes:
            await callback.message.answer("Каталог пуст. Нечего редактировать.",reply_markup=await admin_keyboard())
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=shoe['name'], callback_data=f"edit_shoe_{shoe['id']}")]
            for shoe in shoes
        ])
        await callback.message.answer("Выберите модель обуви для редактирования:", reply_markup=keyboard)


@admin_router.callback_query(F.data.startswith("edit_shoe_"))
async def select_edit_shoe_callback(callback: CallbackQuery, state: FSMContext, pool):
    shoe_id = int(callback.data.split("_")[2])
    await state.update_data(shoe_id=shoe_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_name_{shoe_id}")],
            [InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_price_{shoe_id}")]
        ]
    )

    await callback.message.answer("Выберите, что хотите изменить:", reply_markup=keyboard)


# Callback для редактирования названия обуви
@admin_router.callback_query(F.data.startswith("edit_name_"))
async def edit_shoe_name_callback(callback: CallbackQuery, state: FSMContext):
    shoe_id = int(callback.data.split("_")[2])
    await state.update_data(shoe_id=shoe_id)
    await callback.message.answer("Введите новое название модели обуви:")
    await state.set_state(AdminActions.EDIT_SHOE_NAME)


@admin_router.callback_query(F.data.startswith("edit_price_"))
async def edit_shoe_price_callback(callback: CallbackQuery, state: FSMContext):
    shoe_id = int(callback.data.split("_")[2])
    await state.update_data(shoe_id=shoe_id)
    await callback.message.answer("Введите новую цену для модели обуви:")
    await state.set_state(AdminActions.EDIT_SHOE_PRICE)


@admin_router.message(AdminActions.EDIT_SHOE_NAME)
async def update_shoe_name(message: Message, state: FSMContext, pool):
    new_name = message.text
    data = await state.get_data()
    shoe_id = data['shoe_id']
    async with pool.acquire() as conn:
        try:
            await conn.execute("UPDATE shoes SET name = $1 WHERE id = $2", new_name, shoe_id)
            await message.answer(f"Название модели обуви изменено на '{new_name}'.", reply_markup=await admin_keyboard())
        except Exception as e:
            print(f"Ошибка при обновлении названия обуви: {e}")
            await message.answer("Произошла ошибка при обновлении названия обуви.", reply_markup=await admin_keyboard())
    await state.clear()


@admin_router.message(AdminActions.EDIT_SHOE_PRICE)
async def update_shoe_price(message: Message, state: FSMContext, pool):
    new_price = message.text
    if not new_price.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return
    data = await state.get_data()
    shoe_id = data['shoe_id']
    new_price = int(new_price)
    async with pool.acquire() as conn:
        try:
            await conn.execute("UPDATE shoes SET price = $1 WHERE id = $2", new_price, shoe_id)
            await message.answer(f"Цена модели обуви изменена на {new_price} рублей.", reply_markup=await admin_keyboard())
        except Exception as e:
            print(f"Ошибка при обновлении цены обуви: {e}")
            await message.answer("Произошла ошибка при обновлении цены обуви.", reply_markup=await admin_keyboard())
    await state.clear()
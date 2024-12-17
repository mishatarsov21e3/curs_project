from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from src.keyboards import start_keyboard
from src.states import SendAdminMessage, Payment, PurchaseShoe
from config import ADMIN_ID
from create_global import bot

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message):
    try:
        start_message_if_user_exist = f"Приветствую тебя {message.from_user.full_name} в моем магазине обуви!\nХочешь что-то заказать?"
        await message.answer(start_message_if_user_exist, reply_markup=await start_keyboard())
    except Exception as e:
        print(e)
        await message.answer("Произошла ошибка...")


@router.message(Command('help'))
@router.message(F.text == "Связаться")
async def help_users(message: Message):
    try:
        help_message = f"{message.from_user.full_name} у тебя как я понял возникла проблема... Свяжись пожалуйста с ним: @taras797\n Или напишите на почту: khormalinskiy@bk.ru"
        await message.answer(help_message, reply_markup=await start_keyboard())
    except Exception as e:
        print(e)
        await message.answer("Произошла ошибка...")


@router.message(Command('feedback'))
@router.message(F.text == "Отзыв")
async def feedback_at_user(message: Message, state: FSMContext):
    await message.answer("Напишите свой отзыв и он отправиться администратору!")
    await state.set_state(SendAdminMessage.admin_message)


@router.message(SendAdminMessage.admin_message)
async def send_message(message: Message, state: FSMContext):
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Отзыв от {message.from_user.full_name}(Имя пользователя: {message.from_user.username}): {message.text}"
    )
    await message.answer("Сообщение успешно отправлено администратору!", reply_markup=await start_keyboard())
    await state.clear()


@router.message(Command('profile'))
@router.message(F.text == "Профиль")
async def profile(message: Message, pool):
    user_id = message.from_user.id
    async with pool.acquire() as conn:
        try:
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            if not user:
                await message.answer("Пользователь не найден в базе данных.", reply_markup=await start_keyboard())
            else:
                profile_text = "Ваш профиль:\n\n"
                profile_text += f"Имя пользователя: {user['user_name']}\n"
                profile_text += f"Баланс: {float(user['balance'])} рублей\n"
                await message.answer(profile_text, reply_markup=await start_keyboard())
        except Exception as e:
            print(e)
            await message.answer("Произошла ошибка...", reply_markup=await start_keyboard())


@router.message(Command('pay'))
@router.message(F.text == "Пополнить баланс")
async def pay(message: Message, state: FSMContext):
    await message.answer("Введите сумму, на которую хотите пополнить свой баланс:")
    await state.set_state(Payment.amount)


@router.message(Payment.amount)
async def update_balance_amount(message: Message, state: FSMContext, pool):
    user_id = message.from_user.id
    amount = message.text
    if not amount.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return

    amount = int(amount)

    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
                amount,
                user_id
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type) VALUES ($1, $2, 'deposit')",
                user_id,
                amount
            )

            await message.answer(f"Платеж на сумму {amount} рублей прошел успешно!",
                                 reply_markup=await start_keyboard())
            await state.clear()

        except Exception as e:
            print(f"Ошибка при обновлении баланса: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже...", reply_markup=await start_keyboard())


@router.message(F.text == 'Каталог')
@router.message(Command('catalog'))
async def catalog_panel(message: Message, pool):
    async with pool.acquire() as conn:
        try:
            shoes = await conn.fetch("SELECT * FROM shoes")
            if not shoes:
                await message.answer("Каталог пуст. Попробуйте позже...", reply_markup=await start_keyboard())
            else:
                catalog_text = "Доступная обувь:\n\n"
                buttons = []
                for shoe in shoes:
                    catalog_text += f"{shoe['name']} - {shoe['price']} рублей\n"
                    buttons.append(
                        [InlineKeyboardButton(text=f"Купить {shoe['name']}",
                                              callback_data=f"buy_shoe_{shoe['id']}")]
                    )
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer(catalog_text, reply_markup=keyboard)
        except Exception as e:
            print(e)
            await message.answer("Произошла ошибка...", reply_markup=await start_keyboard())


@router.callback_query(F.data.startswith('buy_shoe_'))
async def buy_shoe_callback(callback: CallbackQuery, state: FSMContext, pool):
    shoe_id = int(callback.data.split('_')[2])
    async with pool.acquire() as conn:
        shoe = await conn.fetchrow("SELECT * FROM shoes WHERE id = $1", shoe_id)
        if not shoe:
            await callback.message.answer("Обувь не найдена.", reply_markup=await start_keyboard())
            return
        user_id = callback.from_user.id
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if not user:
            await callback.message.answer("Пользователь не найден.", reply_markup=await start_keyboard())
            return
        if user['balance'] < shoe['price']:
            await callback.message.answer("Недостаточно средств на балансе. Пожалуйста, пополните баланс.",
                                          reply_markup=await start_keyboard())
            return
        await state.set_state(PurchaseShoe.confirm)
        await state.update_data(shoe_id=shoe_id, price=shoe['price'])
        await callback.message.answer(f"Вы хотите купить {shoe['name']} за {shoe['price']} рублей. Подтвердим покупку?",
                                      reply_markup=InlineKeyboardMarkup(
                                          inline_keyboard=[
                                              [InlineKeyboardButton(text="Подтвердить",
                                                                    callback_data="confirm_purchase")],
                                              [InlineKeyboardButton(text="Отменить", callback_data="cancel_purchase")]
                                          ]
                                      ))


@router.callback_query(F.data == "confirm_purchase", PurchaseShoe.confirm)
async def confirm_purchase_callback(callback: CallbackQuery, state: FSMContext, pool):
    data = await state.get_data()
    shoe_id = data.get('shoe_id')
    price = data.get('price')
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        try:
            await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", price, user_id)
            order_id = await conn.fetchval(
                "INSERT INTO orders (user_id, shoe_id, quantity, total_price, status) VALUES ($1, $2, 1, $3, 'pending') RETURNING id",
                user_id, shoe_id, price
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type) VALUES ($1, $2, 'purchase')",
                user_id, price
            )
            await callback.message.answer("Ваш заказ отправлен на подтверждение администратору.",
                                          reply_markup=await start_keyboard())

            # Notify admin
            shoe = await conn.fetchrow("SELECT * FROM shoes WHERE id = $1", shoe_id)
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            admin_message = f"Новый заказ:\n" \
                            f"ID: {user_id}\n" \
                            f"Имя пользователя: {user['user_name']}\n" \
                            f"Обувь: {shoe['name']} - {shoe['price']} руб.\n" \
                            f"ID заказа: {order_id}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить", callback_data=f"approve_order_{order_id}")],
                    [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_order_{order_id}")]
                ]
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message, reply_markup=keyboard)

        except Exception as e:
            print(f"Ошибка при покупке обуви: {e}")
            await callback.message.answer("Произошла ошибка при покупке. Пожалуйста, попробуйте позже.",
                                          reply_markup=await start_keyboard())
    await state.clear()


@router.callback_query(F.data == "cancel_purchase", PurchaseShoe.confirm)
async def cancel_purchase_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Покупка отменена.", reply_markup=await start_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("approve_order_"))
async def approve_order_callback(callback: CallbackQuery, pool):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("У вас нет权限 для этого действия.")
        return
    order_id = int(callback.data.split("_")[2])
    async with pool.acquire() as conn:
        try:
            order = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            if not order:
                await callback.message.answer("Заказ не найден.")
                return
            await conn.execute("UPDATE orders SET status = 'completed' WHERE id = $1", order_id)
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", order['user_id'])
            await bot.send_message(
                chat_id=order['user_id'],
                text="Ваш заказ подтвержден и будет обработан."
            )
            await callback.message.answer(f"Заказ {order_id} подтвержден.")
        except Exception as e:
            print(f"Ошибка при подтверждении заказа: {e}")
            await callback.message.answer("Произошла ошибка при подтверждении заказа.")


@router.callback_query(F.data.startswith("reject_order_"))
async def reject_order_callback(callback: CallbackQuery, pool):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("У вас нет权限 для этого действия.")
        return
    order_id = int(callback.data.split("_")[2])
    async with pool.acquire() as conn:
        try:
            order = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            if not order:
                await callback.message.answer("Заказ не найден.")
                return
            await conn.execute("UPDATE orders SET status = 'rejected' WHERE id = $1", order_id)
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
                order['total_price'], order['user_id']
            )
            await bot.send_message(
                chat_id=order['user_id'],
                text="Ваш заказ был отклонен. Средства возвращены на баланс."
            )
            await callback.message.answer(f"Заказ {order_id} отклонен.")
        except Exception as e:
            print(f"Ошибка при отклонении заказа: {e}")
            await callback.message.answer("Произошла ошибка при отклонении заказа.")


@router.message(Command("orders"))
@router.message(F.text == "Мои заказы")
async def view_orders(message: Message, pool):
    user_id = message.from_user.id

    async with pool.acquire() as conn:
        try:
            # Получаем заказы пользователя
            orders = await conn.fetch("SELECT * FROM orders WHERE user_id = $1", user_id)

            if not orders:
                await message.answer("У вас пока нет заказов.", reply_markup=await start_keyboard())
                return

            # Формируем сообщение с заказами
            orders_text = "Ваши заказы:\n\n"
            for order in orders:
                shoe = await conn.fetchrow("SELECT * FROM shoes WHERE id = $1", order['shoe_id'])
                if not shoe:
                    shoe_name = "Обувь не найдена"
                else:
                    shoe_name = shoe['name']

                orders_text += f"Заказ №{order['id']}:\n"
                orders_text += f"Обувь: {shoe_name}\n"
                orders_text += f"Количество: {order['quantity']}\n"
                orders_text += f"Общая стоимость: {order['total_price']} рублей\n"
                orders_text += f"Статус: {order['status']}\n\n"

            await message.answer(orders_text, reply_markup=await start_keyboard())

        except Exception as e:
            print(f"Ошибка при получении заказов: {e}")
            await message.answer("Произошла ошибка при получении заказов. Попробуйте позже.",
                                 reply_markup=await start_keyboard())

from aiogram.fsm.state import State, StatesGroup


class SendAdminMessage(StatesGroup):
    admin_message = State()


class Payment(StatesGroup):
    amount = State()


class PurchaseShoe(StatesGroup):
    confirm = State()


class AdminActions(StatesGroup):
    ADD_SHOE_NAME = State()
    ADD_SHOE_PRICE = State()
    DELETE_SHOE_SELECT = State()
    EDIT_SHOE_SELECT = State()
    EDIT_SHOE_NAME = State()
    EDIT_SHOE_PRICE = State()

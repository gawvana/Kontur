from aiogram.fsm.state import State, StatesGroup

class AddForm(StatesGroup):
    waiting_for_data = State()
    confirm = State()

class AppealForm(StatesGroup):
    waiting_for_reason = State()
    waiting_for_evidence = State()

class SupportForm(StatesGroup):
    waiting_for_message = State()

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.forms import AddForm

router = Router()

@router.message(Command("catalogs"))
async def cmd_catalogs(message: Message):
    await message.answer("Каталоги через бота пока недоступны.")

@router.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("Поиск через бота пока не реализован.")

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await state.set_state(AddForm.waiting_for_data)
    await message.answer("Please send the data to add to the catalog:")

@router.message(AddForm.waiting_for_data)
async def process_add_data(message: Message, state: FSMContext):
    await state.update_data(data=message.text)
    await state.set_state(AddForm.confirm)
    await message.answer("Are you sure you want to add this? (yes/no)")

@router.message(AddForm.confirm)
async def process_add_confirm(message: Message, state: FSMContext):
    if (message.text or "").strip().lower() == "yes":
        await message.answer("Добавление не выполнено: сохранение контактов через бота пока не реализовано.")
    else:
        await message.answer("Cancelled.")
    await state.clear()

@router.message(Command("review"))
async def cmd_review(message: Message):
    await message.answer("Подача отзыва через бота пока не реализована.")

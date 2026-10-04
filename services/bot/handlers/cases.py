from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.forms import AppealForm

router = Router()

@router.message(Command("cases"))
async def cmd_cases(message: Message):
    await message.answer("Просмотр обращений через бота пока не реализован.")

@router.message(Command("appeal"))
async def cmd_appeal(message: Message, state: FSMContext):
    await state.set_state(AppealForm.waiting_for_reason)
    await message.answer("Please describe the reason for your appeal:")

@router.message(AppealForm.waiting_for_reason)
async def process_appeal_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(AppealForm.waiting_for_evidence)
    await message.answer("Please provide evidence (text or link):")

@router.message(AppealForm.waiting_for_evidence)
async def process_appeal_evidence(message: Message, state: FSMContext):
    await message.answer("Апелляция не отправлена: серверный процесс пока не реализован.")
    await state.clear()

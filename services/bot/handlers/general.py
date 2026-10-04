from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.forms import SupportForm

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Контур. Основные действия бота пока не подключены к серверу. /help — команды, /cancel — отмена.")

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer("Настройки через бота пока не реализованы.")

@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext):
    await state.set_state(SupportForm.waiting_for_message)
    await message.answer("Please send your support message:")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("/check /catalogs /add /review /cases /appeal /subscriptions /notifications /settings /support. Серверные сценарии пока недоступны. /cancel отменяет текущий диалог.")

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Диалог отменён.")

@router.message(SupportForm.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    await message.answer("Обращение не отправлено: поддержка через бота пока не реализована.")
    await state.clear()


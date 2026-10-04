from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("subscriptions"))
async def cmd_subscriptions(message: Message):
    await message.answer("Подписки через бота пока не реализованы.")

@router.message(Command("notifications"))
async def cmd_notifications(message: Message):
    await message.answer("Уведомления через бота пока не реализованы.")

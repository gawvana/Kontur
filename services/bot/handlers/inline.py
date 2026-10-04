from aiogram import Router
from aiogram.types import InlineQuery
router = Router()

@router.inline_query()
async def inline_search(inline_query: InlineQuery):
    # No public summaries exist; never fabricate results.
    await inline_query.answer([], is_personal=True, cache_time=0)

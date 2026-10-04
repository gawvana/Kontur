import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from handlers import catalog, cases, general, inline

def run(coro):
    return asyncio.run(coro)

def test_add_never_fakes_success_for_yes_or_non_text():
    for text in ['yes', None]:
        message = SimpleNamespace(text=text, answer=AsyncMock())
        state = SimpleNamespace(clear=AsyncMock())
        run(catalog.process_add_confirm(message,state))
        assert 'success' not in message.answer.call_args.args[0].lower()
        state.clear.assert_awaited_once()

def test_appeal_never_fakes_submission_or_echoes_sensitive_text():
    message=SimpleNamespace(answer=AsyncMock())
    state=SimpleNamespace(clear=AsyncMock(), get_data=AsyncMock(return_value={'reason':'<b>private</b>'}))
    run(cases.process_appeal_evidence(message,state))
    assert 'private' not in message.answer.call_args.args[0]
    assert 'submitted' not in message.answer.call_args.args[0].lower()

def test_support_never_fakes_received():
    message=SimpleNamespace(answer=AsyncMock())
    state=SimpleNamespace(clear=AsyncMock())
    run(general.process_support_message(message,state))
    assert 'received' not in message.answer.call_args.args[0].lower()

def test_cancel_and_help_available_during_state():
    message=SimpleNamespace(answer=AsyncMock())
    state=SimpleNamespace(clear=AsyncMock())
    run(general.cmd_cancel(message,state))
    state.clear.assert_awaited_once()
    handlers=[h.callback.__name__ for h in general.router.message.handlers]
    assert handlers.index('cmd_cancel') < handlers.index('process_support_message')

def test_inline_never_fabricates_public_results():
    query=SimpleNamespace(query='<script>private</script>',answer=AsyncMock())
    run(inline.inline_search(query))
    assert query.answer.call_args.args == ([],)
    assert query.answer.call_args.kwargs['cache_time'] == 0

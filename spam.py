# modules/spam.py
"""
<manifest>
{
  "name": "Spammer",
  "version": "1.0",
  "author": "SynForge",
  "source": "https://<ссылка_на_твой_github>/raw/main/modules/spam.py",
  "channel_url": "https://t.me/SynForge",
  "dependencies": []
}
</manifest>

Модуль для спама сообщениями с поддержкой форматирования.
Автор: @SynForge

Команды:
• spam <количество> <текст> - Начать спам.
• stopspam - Остановить текущую задачу спама.
"""

import asyncio
import re
from telethon.tl.types import MessageEntityBold, MessageEntityCode, MessageEntityCustomEmoji

from core import register
from utils.message_builder import build_and_edit, build_message

# --- ПРЕМИУМ ЭМОДЗИ (замените ID на ваши, полученные через .getid) ---
ROCKET_EMOJI_ID = 5445284980978621387   # Пример 🚀
SUCCESS_EMOJI_ID = 5776375003280838798  # Пример ✅
ERROR_EMOJI_ID = 5778527486270770928    # Пример ❌
INFO_EMOJI_ID = 5879785854284599288     # Пример ℹ️

# Глобальная переменная для хранения активной задачи спама.
SPAM_TASK = None

@register("spam")
async def spam_cmd(event):
    """Начинает спам сообщениями."""
    global SPAM_TASK

    if SPAM_TASK and not SPAM_TASK.done():
        return await build_and_edit(event, [
            {"text": "❌", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": ERROR_EMOJI_ID}},
            {"text": " Спам уже запущен. Остановите его командой .stopspam", "entity": MessageEntityBold}
        ])

    args_str = (event.pattern_match.group(1) or "").strip()
    
    count = 20
    text_to_spam = args_str

    match = re.match(r"(\d+)\s+(.*)", args_str, re.DOTALL)
    if match:
        count = int(match.group(1))
        text_to_spam = match.group(2)
    
    if not text_to_spam:
        return await build_and_edit(event, [
            {"text": "❌", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": ERROR_EMOJI_ID}},
            {"text": " Укажите текст для спама.", "entity": MessageEntityBold}
        ])

    command_prefix_len = len(event.text.split(text_to_spam, 1)[0])
    entities = []
    if event.message.entities:
        for entity in event.message.entities:
            if entity.offset >= command_prefix_len:
                new_entity = entity.copy()
                new_entity.offset -= command_prefix_len
                entities.append(new_entity)
    
    async def spam_worker():
        global SPAM_TASK
        try:
            tasks = [
                event.client.send_message(event.chat_id, text_to_spam, formatting_entities=entities)
                for _ in range(count)
            ]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            await event.client.send_message(
                event.chat_id, 
                "**✅ Спам принудительно остановлен.**", 
                parse_mode="md"
            )
        except Exception as e:
            await event.client.send_message(
                event.chat_id,
                f"**❌ Произошла ошибка во время спама:**\n`{e}`",
                parse_mode="md"
            )
        finally:
            SPAM_TASK = None
    
    SPAM_TASK = asyncio.create_task(spam_worker())
    
    await event.delete()
    
    confirm_parts = [
        {"text": "🚀", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": ROCKET_EMOJI_ID}},
        {"text": " Спам запущен! ", "entity": MessageEntityBold},
        {"text": "Количество: ", "entity": MessageEntityBold},
        {"text": str(count), "entity": MessageEntityCode}
    ]
    text, entities = build_message(confirm_parts)
    await event.client.send_message(event.chat_id, text, formatting_entities=entities)


@register("stopspam")
async def stopspam_cmd(event):
    """Останавливает текущую задачу спама."""
    global SPAM_TASK
    
    if not SPAM_TASK or SPAM_TASK.done():
        return await build_and_edit(event, [
            {"text": "ℹ️", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": INFO_EMOJI_ID}},
            {"text": " Активных задач спама нет.", "entity": MessageEntityBold}
        ])

    SPAM_TASK.cancel()
    await event.delete()
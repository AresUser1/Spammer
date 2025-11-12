# modules/Spammer/spam.py
"""
<manifest>
name: Spammer
version: 1.1.6
author: SynForge
source: https://raw.githubusercontent.com/AresUser1/Spammer/main/spam.py
channel_url: https://t.me/SynForge
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

# --- ПРЕМИУМ ЭМОДЗИ (замените ID на ваши) ---
ROCKET_EMOJI_ID = 5445284980978621387   # 🚀
SUCCESS_EMOJI_ID = 5776375003280838798  # ✅
ERROR_EMOJI_ID = 5778527486270770928    # ❌
INFO_EMOJI_ID = 5879785854284599288     # ℹ️

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

    # --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: НАДЕЖНЫЙ ПАРСИНГ АРГУМЕНТОВ И КООРДИНАТ ---
    
    # Текст, который идет после команды (например, "10 **Привет**")
    args_text = event.pattern_match.group(1) or ""
    # Координата в event.text, где этот текст начинается
    args_start_offset = event.pattern_match.start(1)

    count = 20
    text_to_spam = ""
    text_start_offset = args_start_offset  # По умолчанию, текст начинается там же, где и аргументы

    # Ищем число в начале строки аргументов
    match = re.match(r"(\d+)\s+", args_text)
    if match:
        count = int(match.group(1))
        # Текст для спама - это всё, что после числа и пробела
        text_to_spam = args_text[match.end():]
        # Сдвигаем начальную координату текста, учитывая длину числа и пробела
        text_start_offset += match.end()
    else:
        # Если числа нет, вся строка - это текст
        text_to_spam = args_text

    if not text_to_spam:
        return await build_and_edit(event, [
            {"text": "❌", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": ERROR_EMOJI_ID}},
            {"text": " Укажите текст для спама.", "entity": MessageEntityBold}
        ])

    entities = []
    if event.message.entities:
        for entity in event.message.entities:
            # Копируем только те стили, которые находятся внутри нашего текста для спама
            if entity.offset >= text_start_offset:
                entity_dict = entity.to_dict()
                if '_' in entity_dict:
                    del entity_dict['_']
                new_entity = type(entity)(**entity_dict)
                # Смещаем координату стиля к началу новой строки
                new_entity.offset -= text_start_offset
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
            await event.client.send_message(event.chat_id, "**✅ Спам принудительно остановлен.**", parse_mode="md")
        except Exception as e:
            await event.client.send_message(event.chat_id, f"**❌ Произошла ошибка во время спама:**\n`{e}`", parse_mode="md")
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
    text, built_entities = build_message(confirm_parts)
    await event.client.send_message(event.chat_id, text, formatting_entities=built_entities)

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

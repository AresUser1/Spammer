# modules/Spammer/spam.py
"""
<manifest>
name: Spammer
version: 1.1.7
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
from telethon.tl.types import (
    MessageEntityBold, MessageEntityCode, MessageEntityCustomEmoji,
    MessageEntityBlockquote # <-- ДОБАВЛЕН ИМПОРТ ЦИТАТЫ
)

from core import register
from utils.message_builder import build_and_edit, build_message

# --- ПРЕМИУМ ЭМОДЗИ (замените ID на ваши) ---
ROCKET_EMOJI_ID = 5445284980978621387
SUCCESS_EMOJI_ID = 5776375003280838798
ERROR_EMOJI_ID = 5778527486270770928
INFO_EMOJI_ID = 5879785854284599288

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

    # --- 1. Парсинг аргументов команды ---
    args_text = event.pattern_match.group(1) or ""
    args_start_offset = event.pattern_match.start(1)

    count = 20
    user_text = ""
    user_text_start_offset = args_start_offset

    match = re.match(r"(\d+)\s+", args_text)
    if match:
        count = int(match.group(1))
        user_text = args_text[match.end():]
        user_text_start_offset += match.end()
    else:
        user_text = args_text

    # --- 2. Определение текста и стилей (entities) для спама ---
    text_to_spam = ""
    entities_to_spam = []

    replied_msg = await event.get_reply_message()

    if replied_msg:
        replied_text = replied_msg.text or ""
        replied_entities = replied_msg.entities or []

        if user_text:
            # СЛУЧАЙ 1: Ответ + свой текст (делаем цитату)
            text_to_spam = replied_text + "\n" + user_text
            
            # Добавляем стиль "цитата" для всего отвеченного текста
            if replied_text:
                entities_to_spam.append(
                    MessageEntityBlockquote(offset=0, length=len(replied_text))
                )
            
            # Добавляем оригинальные стили из ответа
            entities_to_spam.extend(replied_entities)

            # Добавляем стили из *нового* текста пользователя (смещаем их)
            user_entities_offset = len(replied_text) + 1
            if event.message.entities:
                for entity in event.message.entities:
                    if entity.offset >= user_text_start_offset:
                        entity_dict = entity.to_dict()
                        if '_' in entity_dict: del entity_dict['_']
                        new_entity = type(entity)(**entity_dict)
                        
                        new_entity.offset = new_entity.offset - user_text_start_offset + user_entities_offset
                        entities_to_spam.append(new_entity)
        
        else:
            # СЛУЧАЙ 2: Ответ без своего текста (просто спамим ответом)
            text_to_spam = replied_text
            entities_to_spam = replied_entities

    else:
        # СЛУЧАЙ 3: Не ответ (исходное поведение)
        text_to_spam = user_text
        if event.message.entities:
            for entity in event.message.entities:
                if entity.offset >= user_text_start_offset:
                    entity_dict = entity.to_dict()
                    if '_' in entity_dict: del entity_dict['_']
                    new_entity = type(entity)(**entity_dict)
                    new_entity.offset -= user_text_start_offset
                    entities_to_spam.append(new_entity)

    # --- 3. Проверка, есть ли что спамить ---
    if not text_to_spam:
        return await build_and_edit(event, [
            {"text": "❌", "entity": MessageEntityCustomEmoji, "kwargs": {"document_id": ERROR_EMOJI_ID}},
            {"text": " Не найден текст для спама. "
                     "Напишите текст или ответьте на сообщение.", "entity": MessageEntityBold}
        ])

    # --- 4. Запуск задачи спама (воркер) ---
    async def spam_worker():
        global SPAM_TASK
        try:
            tasks = [
                event.client.send_message(
                    event.chat_id, 
                    text_to_spam, 
                    formatting_entities=entities_to_spam # ИСПОЛЬЗУЕМ entities_to_spam
                )
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

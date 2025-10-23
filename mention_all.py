import logging
from telethon.errors import ChatAdminRequiredError, UserPrivacyRestrictedError
from telethon.tl.types import MessageEntityMentionName

async def mention_all(client, chat_id, limit=50):
    """
    Пингует всех участников в группе (до `limit` человек).
    Игнорирует ботов и корректно формирует упоминания через MessageEntityMentionName.
    """
    try:
        participants = await client.get_participants(chat_id, limit=limit)
        mentions = []
        message_text = ""

        for user in participants:
            if user.bot:
                continue
            name = user.first_name or "Безымянный"
            entity = MessageEntityMentionName(
                offset=len(message_text),
                length=len(name),
                user_id=user.id
            )
            mentions.append(entity)
            message_text += f"{name} "

        if message_text.strip():
            await client.send_message(chat_id, message_text.strip(), entities=mentions)
        else:
            await client.send_message(chat_id, "⚠️ Не удалось найти участников для упоминания.")

    except ChatAdminRequiredError:
        await client.send_message(chat_id, "❌ Нужны права администратора, чтобы получить участников.")
    except UserPrivacyRestrictedError:
        await client.send_message(chat_id, "⚠️ У некоторых пользователей закрыты упоминания.")
    except Exception as e:
        logging.exception(e)
        await client.send_message(chat_id, f"⚠️ Ошибка: {e}")

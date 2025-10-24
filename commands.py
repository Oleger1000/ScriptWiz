import weather, schedule_npi
from json_state import save_state
from config import WEATHER_STATE_FILE, SCHEDULE_STATE_FILE, CONTROL_CHAT_ID, AVATARS_DIR, MUSIC_STATE_FILE
import logging
from mention_all import mention_all

# в начале файла
from images import get_random_avatar, prepare_image
from telethon.tl.functions.photos import UploadProfilePhotoRequest


async def handle_command(client, event, states, music_manager):
    text = event.raw_text.strip().lower()
    chat_id = event.chat_id
    weather_enabled = states['weather']
    avatar_enabled = states['avatar']
    schedule_enabled = states['schedule']

    # Удаляем команды с префиксом !
    if text.startswith('!'):
        await client.delete_messages(chat_id, [event.id])
        parts = text[1:].split()
        command = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        match command:
            case "погода":
                await weather.send_weather_card(client, chat_id, weather_enabled)
            case "расписание":
                if arg:
                    await schedule_npi.send_schedule(client, chat_id, arg.upper())
                else:
                    await client.send_message(chat_id, "❌ Укажи группу: POV или KMS")
            case "all":
                await mention_all(client, chat_id)
        return

    # Контрольный чат
    if chat_id != CONTROL_CHAT_ID:
        return

    logging.info(f"Получено сообщение в контрольном чате: {text}")

    match text:
        case "вкл_погода":
            states['weather'] = True
            save_state(WEATHER_STATE_FILE, True)
            await event.reply("✅ Прогноз погоды включён.")
        case "выкл_погода":
            states['weather'] = False
            save_state(WEATHER_STATE_FILE, False)
            await event.reply("❌ Прогноз погоды выключен.")
        case "вкл_аватар":
            states['avatar'] = True
            await event.reply("✅ Автосмена аватарок включена.")
        case "выкл_аватар":
            states['avatar'] = False
            await event.reply("❌ Автосмена аватарок выключена.")
        case "сменить аватар":
            if states['avatar']:
                avatar_path = get_random_avatar(AVATARS_DIR)
                if avatar_path:
                    tmp_path = prepare_image(avatar_path)
                    file = await client.upload_file(tmp_path)
                    await client(UploadProfilePhotoRequest(file=file))
                    await event.reply("🖼 Аватарка обновлена!")
                else:
                    await event.reply("⚠️ Нет доступных аватарок.")
            else:
                await event.reply("⚠️ Автосмена аватарок выключена.")
        case "вкл_расписание":
            states['schedule'] = True
            save_state(SCHEDULE_STATE_FILE, True)
            await event.reply("✅ Расписание включено.")
        case "выкл_расписание":
            states['schedule'] = False
            save_state(SCHEDULE_STATE_FILE, False)
            await event.reply("❌ Расписание выключено.")
        case "выкл_музыка":
            if music_manager:
                music_manager.disable_with_placeholder()
            states['music'] = False
            save_state(MUSIC_STATE_FILE, False)
            await event.reply("❌ Живой статус музыки выключен. Установлен статичный плейсхолдер.")

        case "вкл_музыка":
            if music_manager:
                music_manager.enable()
                await music_manager.update_music_status(music_manager.current_status)
            states['music'] = True
            save_state(MUSIC_STATE_FILE, True)
            await event.reply("✅ Живой статус музыки включён.")

        case "статус":
            status_text = (
                f"🌦 Погода: {'включён ✅' if states['weather'] else 'выключен ❌'}\n"
                f"🖼 Автосмена аватарок: {'включена ✅' if states['avatar'] else 'выключена ❌'}\n"
                f"📅 Расписание: {'включено ✅' if states['schedule'] else 'выключено ❌'}"
                f"🎵 Музыка: {'включен ✅' if states['music'] else 'выключен ❌'}\n"

            )
            await event.reply(status_text)
        case "help":
            help_text = (
                "📜 Доступные команды:\n\n"
                "вкл_погода / выкл_погода — управление прогнозом\n"
                "вкл_аватар / выкл_аватар — управление аватарками\n"
                "сменить аватар — сменить аватарку сейчас\n"
                "вкл_расписание / выкл_расписание — управление расписанием\n"
                "статус — показать статусы\n"
                "help — показать это сообщение\n\n"
                "В любом чате:\n!погода — отправить прогноз\n!расписание — отправить расписание"
            )
            await event.reply(help_text)
        case _:
            await event.reply("❌ Неизвестная команда. Напиши 'help'.")

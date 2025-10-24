import asyncio
import logging
import schedule
from telethon import TelegramClient, events
from config import *
from json_state import load_state
from music_status import MusicStatusManager, init_music_manager, start_web_server
from commands import handle_command
from images import get_random_avatar, prepare_image
from weather import send_weather_card
from schedule_npi import send_schedule

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Инициализация клиента
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
from music_status import init_music_manager
music_manager = init_music_manager(client)



# Состояния
states = {
    'weather': load_state(WEATHER_STATE_FILE, False),
    'avatar': True,
    'schedule': load_state(SCHEDULE_STATE_FILE, True),
    'music': load_state(MUSIC_STATE_FILE, True)
}

# Проверка перед отправкой
async def job_weather():
    if states['weather']:
        await send_weather_card(client, GROUP_CHAT_ID, states['weather'])

async def job_schedule_kms():
    if states['schedule']:
        await send_schedule(client, GROUP_CHAT_ID, "KMS")

async def job_schedule_pov():
    if states['schedule']:
        await send_schedule(client, S_GROUP_CHAT_ID, "POV")

async def job_avatar():
    if states['avatar']:
        avatar_path = get_random_avatar(AVATARS_DIR)
        if avatar_path:
            tmp_path = prepare_image(avatar_path)
            file = await client.upload_file(tmp_path)
            await client(UploadProfilePhotoRequest(file=file))
            logging.info("🖼 Автосмена аватарки выполнена")
        else:
            logging.warning("⚠️ Нет доступных аватарок для смены")

@client.on(events.NewMessage)
async def on_message(event):
    try:
        await handle_command(client, event, states, music_manager)
    except Exception as e:
        logging.exception(f"Ошибка в обработчике: {e}")

async def scheduler_loop():
    while True:
        schedule.run_pending()
        await asyncio.sleep(30)

async def main():
    await client.start()
    logging.info("🤖 Клиент готов.")

    # Инициализация менеджера музыки ДО запуска web-сервера
    init_music_manager(client)
    
    # Запуск web-сервера для статусов музыки
    port = await start_web_server(8888)  # Используем порт 8889
    if port:
        logging.info(f"✅ Web-сервер запущен на порту {port}")
    else:
        logging.error("❌ Не удалось запустить web-сервер")

    # Планировщик
    schedule.every().day.at("00:00").do(lambda: asyncio.create_task(job_avatar()))
    schedule.every().day.at("07:00").do(lambda: asyncio.create_task(job_weather()))
    schedule.every().day.at("07:00").do(lambda: asyncio.create_task(job_schedule_kms()))
    schedule.every().day.at("07:01").do(lambda: asyncio.create_task(job_schedule_pov()))

    asyncio.create_task(scheduler_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

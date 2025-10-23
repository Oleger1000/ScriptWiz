import asyncio
import logging
import os

async def generate_weather_card():
    process = await asyncio.create_subprocess_shell(
        "./kek.sh",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        logging.error(f"Ошибка генерации картинки: {stderr.decode()}")
        return None
    logging.info(stdout.decode())
    return "weather_card.png"

async def send_weather_card(client, chat_id, weather_enabled):
    if not weather_enabled:
        logging.info("Погода выключена — пропускаю отправку.")
        return

    card_path = await generate_weather_card()
    if not card_path or not os.path.exists(card_path):
        logging.warning("Картинка с погодой не найдена.")
        return

    await client.send_file(chat_id, card_path, caption="🌤 Прогноз погоды на сегодня")
    logging.info(f"Картинка с погодой отправлена в чат {chat_id}!")

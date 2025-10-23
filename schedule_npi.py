import aiohttp
from datetime import datetime
import logging
from config import SCHEDULE_ENDPOINTS

INTERVALS_URL = "https://schedule.npi-tu.ru/api/v1/class-intervals"

async def send_schedule(client, chat_id, group_type):
    schedule_url = SCHEDULE_ENDPOINTS.get(group_type.upper())
    if not schedule_url:
        await client.send_message(chat_id, f"❌ Неправильная группа: {group_type}")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(schedule_url) as resp:
            if resp.status != 200:
                await client.send_message(chat_id, "⚠️ Не удалось получить расписание.")
                return
            schedule_data = await resp.json()

        async with session.get(INTERVALS_URL) as resp:
            if resp.status != 200:
                await client.send_message(chat_id, "⚠️ Не удалось получить интервалы пар.")
                return
            intervals_data = await resp.json()

    today = datetime.now().strftime('%Y-%m-%d')
    today_schedule = [lesson for lesson in schedule_data.get("classes", []) if today in lesson.get("dates", [])]

    if not today_schedule:
        await client.send_message(chat_id, f"📅 Пар на {today} нет.")
        return

    lines = [f"📅 Расписание на {today} ({group_type.upper()}):\n"]
    for lesson in today_schedule:
        class_number = str(lesson['class'])
        time_info = intervals_data.get(class_number, {"start": "??:??", "end": "??:??"})
        lines.append(f"{class_number}. {lesson['discipline']} ({lesson['type']})")
        lines.append(f"   Время: {time_info['start']} - {time_info['end']}")
        lines.append(f"   Аудитория: {lesson['auditorium']}")
        lines.append(f"   Преподаватель: {lesson['lecturer']}\n")
    await client.send_message(chat_id, "\n".join(lines))
    logging.info(f"Расписание ({group_type}) отправлено в чат {chat_id}!")

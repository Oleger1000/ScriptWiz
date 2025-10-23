import os

# Telegram
API_ID = 24419438
API_HASH = 'f61996692d635486ba64466865ac3424'
SESSION_NAME = 'tg_avatar_session'

CONTROL_CHAT_ID = -4899683243
GROUP_CHAT_ID = -1002238157416
S_GROUP_CHAT_ID = -1002645345415

AVATARS_DIR = 'avatars'

# Schedule
SCHEDULE_ENDPOINTS = {
    "POV": "https://schedule.npi-tu.ru/api/v2/faculties/2/years/2/groups/ПОВа/schedule",
    "KMS": "https://schedule.npi-tu.ru/api/v2/faculties/2/years/2/groups/%D0%9A%D0%9C%D0%A1%D0%B0/schedule"
}

# Weather
WEATHER_API_KEY = 'e3b5b977-2b52-4406-8fe6-58ee4bc8cb59'
LAT = 47.42
LON = 40.09
LANG = 'ru_RU'

# State files
WEATHER_STATE_FILE = 'weather_state.json'
SCHEDULE_STATE_FILE = 'schedule_state.json'

# Logging
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'

#!/usr/bin/env python3
# weather_card.py
# Отладочный скрипт: получает данные Yandex Weather SmartHome API и рисует карточку прогноза (PNG).
# Координаты: lat=47.42, lon=40.09
# Кеширует иконки в ./icons/

import os
import io
import math
import time
import requests
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import json


# ================== Настройки ==================
ACCESS_KEY = 'e3b5b977-2b52-4406-8fe6-58ee4bc8cb59'  # вставь свой ключ, если другой
LAT, LON = 47.42, 40.09
LANG = 'ru_RU'

WIDTH, HEIGHT = 800, 1000
OUT_FILE = "weather_card.png"
ICONS_DIR = "icons"

GRAD_TOP = (0x02, 0xC3, 0x8D)   # #FF2CDF
GRAD_BOTTOM = (0x4E, 0x14, 0x8C) # #0014FF

# Попытки найти удобные шрифты; fallback на ImageFont.load_default()
PREFERRED_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

# Яндекс иконки (PNG)
ICON_URL_TEMPLATE = "https://yastatic.net/weather/i/icons/funky/dark/{icon}.svg"

# ================== Утилиты ==================

def ensure_dirs():
    os.makedirs(ICONS_DIR, exist_ok=True)

def choose_font(size, bold=False):
    for p in PREFERRED_FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def fetch_json(from_file=None):
    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    url = f'https://api.weather.yandex.ru/v2/forecast?lat={LAT}&lon={LON}&lang={LANG}&hours=true'
    headers = {'X-Yandex-Weather-Key': ACCESS_KEY}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def download_icon(icon_code):
    if not icon_code:
        return None
    local = os.path.join(ICONS_DIR, f"{icon_code}.png")
    if os.path.exists(local):
        try:
            return Image.open(local).convert("RGBA")
        except Exception:
            os.remove(local)
    url = ICON_URL_TEMPLATE.format(icon=icon_code)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # Конвертируем SVG в PNG с высоким разрешением
        cairosvg.svg2png(bytestring=resp.content, write_to=local, output_width=256, output_height=256)
        return Image.open(local).convert("RGBA")
    except Exception as e:
        print(f"[icon] ошибка загрузки {icon_code}: {e}")
        return None

def diagonal_gradient(img, top_color, bottom_color):
    """Рисует градиент под 45 градусов: цвет зависит от (x+y)/(w+h)."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            ratio = (x + y) / (w + h - 2)
            r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
            draw.point((x, y), fill=(r, g, b))
    del draw

def safe_get(dct, *keys, default=None):
    cur = dct
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def draw_emoji(base_img, emoji_name, xy):
    """Вставляет PNG эмодзи на картинку"""
    path = os.path.join("emoji", f"{emoji_name}.png")
    if not os.path.exists(path):
        return
    try:
        em_img = Image.open(path).convert("RGBA")
        base_img.paste(em_img, xy, em_img)
    except Exception as e:
        print(f"[emoji] ошибка вставки {emoji_name}: {e}")


# ================== Логика обработки часов ==================

def flatten_hours(data):
    """Собирает все 'hours' из forecasts в один список, добавляет hour_ts если нужно."""
    hours = []
    for f in data.get('forecasts', []):
        for h in f.get('hours', []):
            # гарантируем наличие 'hour_ts' (UNIX), если нет — строим из date+hour
            if 'hour_ts' not in h:
                # forecast date возможен в f['date']
                date = f.get('date')  # формат "YYYY-MM-DD"
                try:
                    hr = int(h.get('hour', 0))
                    dt = datetime.strptime(f"{date} {hr}", "%Y-%m-%d %H")
                    # предположим локальное время — переводим в timestamp
                    h['hour_ts'] = int(dt.replace(tzinfo=timezone.utc).timestamp())
                except Exception:
                    h['hour_ts'] = int(time.time())
            hours.append(h)
    # сортируем по timestamp
    hours.sort(key=lambda x: x.get('hour_ts', 0))
    return hours

def select_next_24(hours):
    """Выбирает 24 ближайших часа с момента сейчас."""
    now_ts = int(time.time())
    future = [h for h in hours if h.get('hour_ts', 0) >= now_ts]
    if len(future) < 24:
        # дополним прошлыми (в случае недостатка)
        remaining = 24 - len(future)
        past = [h for h in hours if h.get('hour_ts', 0) < now_ts]
        # берем последние 'remaining' из past
        extra = past[-remaining:] if remaining <= len(past) else past
        future.extend(extra)
    return future[:24]


def select_hours_7_to_22(hours):
    """Выбирает часы текущего дня с 7:00 до 22:00 включительно."""
    from datetime import datetime

    today = datetime.now().date()
    selected = []

    for h in hours:
        ts = h.get('hour_ts', int(time.time()))
        dt = datetime.fromtimestamp(ts)
        if dt.date() == today and 7 <= dt.hour <= 22:
            selected.append(h)

    # Сортируем на всякий случай по timestamp
    selected.sort(key=lambda x: x.get('hour_ts', 0))
    return selected


# ================== Рендер карточки ==================

def generate_card(data):
    ensure_dirs()
    img = Image.new("RGB", (WIDTH, HEIGHT), (255,255,255))
    diagonal_gradient(img, GRAD_TOP, GRAD_BOTTOM)

    draw = ImageDraw.Draw(img)
    font_h1 = choose_font(44)
    font_h2 = choose_font(30)
    font_m = choose_font(22)
    font_small = choose_font(18)

    # Соберём wind/humidity диапазоны для сводки
    wind_vals = []
    hum_vals = []
    # Почасовой прогноз — справа
    # Получим список часов и выберем ближайшие 24
    all_hours = flatten_hours(data)
    hours_24 = select_hours_7_to_22(all_hours)
    
    for h in hours_24:
        if 'wind_speed' in h: 
            try:    
                wind_vals.append(float(h.get('wind_speed', 0)))
            except: 
                pass
        if 'humidity' in h:
            try:
                hum_vals.append(int(h.get('humidity', 0)))
            except:
                pass

    # Шапка
    header_y = 30
    draw.text((40, header_y), "доброе утро!", font=font_h1, fill=(255,255,255))
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    draw.text((40, header_y + 54), date_str, font=font_small, fill=(230,230,230))

    # Текущее состояние
    fact = safe_get(data, 'fact', default={})
    cur_temp = fact.get('temp', '—')
    cur_feels = fact.get('feels_like', '—')
    cur_icon = fact.get('icon')
    cur_cond = fact.get('condition', '').replace('-', ' ')
    cur_wind = fact.get('wind_speed', '—')
    cur_humidity = fact.get('humidity', '—')

    cond_map = {
        "clear": "☀️ ясно",
        "partly-cloudy": "🌤 переменная облачность",
        "cloudy": "☁️ облачно",
        "overcast": "🌫 пасмурно",
        "rain": "🌧 дождь",
        "light-rain": "🌦 небольшой дождь",
        "snow": "❄️ снег",
        "thunderstorm": "⛈ гроза"
    }

    condition_rus = cond_map.get(cur_cond)

    # скачиваем иконку текущей погоды
    icon_img = download_icon(cur_icon)
    # Блок текущей погоды слева
    left_x = 40
    left_y = 140
    if icon_img:
        ic_size = 120
        icon_resized = icon_img.resize((ic_size, ic_size), Image.Resampling.LANCZOS)
        img.paste(icon_resized, (left_x, left_y), icon_resized)
        left_x += ic_size + 20

    draw.text((left_x, left_y + 10), f"{cur_temp}°C", font=choose_font(64), fill=(255,255,255))
    draw.text((left_x, left_y + 80), f"ощущ. как {cur_feels}°C — {condition_rus}", font=font_h2, fill=(245,245,245))

    # Сейчас: влага и ветер
    draw.text((40, left_y + 160), f"Влажность: {min(hum_vals)}–{max(hum_vals)}%", font=font_m, fill=(255,255,255))
    draw.text((40, left_y + 189), f"Ветер: {min(wind_vals):.1f}–{max(wind_vals):.1f} м/с", font=font_m, fill=(255,255,255))


    # Рассвет/закат берём из forecasts[0] если есть
    first_fc = safe_get(data, 'forecasts', default=[{}])[0]
    sunrise = first_fc.get('sunrise') or ''
    sunset = first_fc.get('sunset') or ''
    rise_begin = first_fc.get('rise_begin') or ''
    set_end = first_fc.get('set_end') or ''

    draw.text((40, left_y + 230), f"Рассвет: {rise_begin} → {sunrise}", font=font_m, fill=(255,255,255))
    draw.text((40, left_y + 260), f"Закат: {sunset} → {set_end}", font=font_m, fill=(255,255,255))

    # Разметка таблицы: справа область
    table_x = 40
    table_y = 400
    table_w = WIDTH - 2 * 40
    # Определим колонки: покажем 2 колонки по 12 часов каждая
    col_count = 2
    rows_per_col = math.ceil(len(hours_24) / col_count)
    col_w = (table_w - 20) // col_count
    row_h = 56

    
    # таблица заголовок
    draw.text((40, table_y + 40), "Прогноз по часам:", font=font_h2, fill=(255,255,255))

    # рисуем строки
    for idx, hour in enumerate(hours_24):
        col = idx // rows_per_col
        row = idx % rows_per_col
        x = 50 + col * (col_w + 10)
        y = table_y + row * row_h + 100

        # час
        # часовое представление: попробуем час из hour['hour'] или сформируем из hour_ts
        hr_txt = None
        if 'hour' in hour:
            hr_txt = f"{int(hour['hour']):02d}:00"
        else:
            ts = hour.get('hour_ts', int(time.time()))
            hr_txt = datetime.fromtimestamp(ts).strftime("%H:00")

        t = hour.get('temp', '—')
        feels = hour.get('feels_like', '—')
        cond_icon = hour.get('icon')
        wind = hour.get('wind_speed', '—')
        hum = hour.get('humidity', '—')

        # иконка
        small_icon = None
        if cond_icon:
            small_icon = download_icon(cond_icon)
            if small_icon:
                small_icon = small_icon.resize((28, 28), Image.Resampling.LANCZOS)


        # рисуем текст строки
        draw.text((x, y), hr_txt, font=font_small, fill=(240,240,240))
        draw.text((x + 98, y), f"{t}° ({feels}°)", font=font_small, fill=(255,255,255))
        draw.text((x + 198, y), f"{wind} м/с", font=font_small, fill=(255,255,255))
        draw.text((x + 278, y), f"{hum}%", font=font_small, fill=(255,255,255))


        # вставляем иконку (если есть) слева от часа
        if small_icon:
            img.paste(small_icon, (x + 65, y - 4), small_icon)
    # Подвал
    draw.text((WIDTH//2 - 150, HEIGHT - 60), "все давай удачи", font=font_h2, fill=(255,255,255))

    # Сохраняем
    img.save(OUT_FILE, format="PNG")
    print(f"[ok] Сохранено: {OUT_FILE}")

# ================== Main ==================

def main():
    print("[*] Получаем данные с Yandex Weather API...")
    try:
        data = fetch_json(from_file="response.json")
    except Exception as e:
        print(f"[err] Не удалось получить данные: {e}")
        return
    generate_card(data)

if __name__ == "__main__":
    main()


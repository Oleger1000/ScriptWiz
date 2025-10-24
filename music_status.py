import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
import json
from json_state import save_state, load_state
from telethon.tl.functions.account import UpdateProfileRequest

STATE_FILE = "music_state.json"



class MusicStatusManager:
    def __init__(self, client):
        self.client = client
        self.current_status = None
        self.last_update = None
        self.is_enabled = True  # live-режим
        self.forced_status = None  # принудительный статус (плейсхолдер)

    async def update_music_status(self, track_info):
        # Если forced_status задан — блокируем любые новые треки
        if self.forced_status:
            if self.current_status != self.forced_status:
                try:
                    await self.client(UpdateProfileRequest(about=self.forced_status[:70]))
                    self.current_status = self.forced_status
                    logging.info(f"⏸ Forced placeholder установлен: {self.forced_status}")
                except Exception as e:
                    logging.error(f"Ошибка установки forced placeholder: {e}")
            return  # трек игнорируем полностью
        
        if not self.is_enabled and self.forced_status:
            logging.debug("🎵 Игнорируем обновление, live выключен")
            return

        if not self.is_enabled:
            return  # live выключен без forced_status

        # Ограничение по частоте обновлений
        if (self.last_update and datetime.now() - self.last_update < timedelta(seconds=30)
            and self.current_status == track_info):
            return

        try:
            about = f"🎵 {track_info}" if track_info else ""
            about = about[:70]
            await self.client(UpdateProfileRequest(about=about))
            self.current_status = track_info
            self.last_update = datetime.now()
            logging.info(f"🎵 Обновлен статус профиля: {track_info}")
        except Exception as e:
            logging.error(f"Ошибка обновления статуса: {e}")

    def disable_with_placeholder(self):
        self.is_enabled = False
        self.forced_status = "🎵 Музыка приостановлена"
        self.current_status = self.forced_status  # <--- вот это критично
        save_state(STATE_FILE, False)
        try:
            self.client(UpdateProfileRequest(about=self.forced_status[:70]))
            logging.info("⏸ Музыкальный статус выключен и установлен forced placeholder")
        except Exception as e:
            logging.error(f"Ошибка при установке forced placeholder: {e}")


    def enable(self):
        self.is_enabled = True
        self.forced_status = None  # снимаем блокировку
        save_state(STATE_FILE, True)
        logging.info("▶ Live-статус музыки включен")
        # сброс таймера last_update, чтобы следующий трек сразу обновил статус
        self.last_update = None



# Глобальная переменная для менеджера - ИНИЦИАЛИЗИРУЕМ КАК None
music_manager = None

# Web-сервер для приема статусов
async def handle_music_update(request):
    """Обработчик POST запросов с информацией о треке"""
    global music_manager
    
    try:
        # Проверяем инициализирован ли music_manager
        if music_manager is None:
            logging.error("❌ MusicManager не инициализирован")
            return web.json_response(
                {'status': 'error', 'message': 'Music manager not initialized'}, 
                status=500
            )
        
        data = await request.json()
        track_info = data.get('track', '').strip()
        
        logging.info(f"🎵 Получен трек от клиента: {track_info}")
        
        if not music_manager.is_enabled:
            # статус выключен — ставим плейсхолдер
            await music_manager.disable_with_placeholder()
            return web.json_response({'status': 'disabled', 'message': 'Live music disabled. Placeholder set.'})

        if track_info:
            await music_manager.update_music_status(track_info)
            return web.json_response({'status': 'success'})
        else:
            await music_manager.update_music_status(None)
            return web.json_response({'status': 'cleared'})

            
    except Exception as e:
        logging.error(f"Ошибка обработки запроса: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=400)



async def handle_toggle(request):
    """Обработчик переключения статуса (вкл/выкл)"""
    global music_manager
    if music_manager is None:
        return web.json_response({'status': 'error', 'message': 'Music manager not initialized'}, status=500)
    
    data = await request.json()
    action = data.get('action', '').lower()
    
    if action == 'enable':
        music_manager.enable()
        # Обновляем текущий статус сразу
        await music_manager.update_music_status(music_manager.current_status)
        return web.json_response({'status': 'enabled'})
    elif action == 'disable':
        await music_manager.disable_with_placeholder()
        return web.json_response({'status': 'disabled'})
    else:
        return web.json_response({'status': 'error', 'message': 'Unknown action'}, status=400)

    
async def handle_get_state(request):
    """Возвращает текущее состояние музыки для клиента"""
    global music_manager
    if music_manager is None:
        return web.json_response({'enabled': False})

    # live включён только если is_enabled=True и forced_status нет
    live_active = music_manager.is_enabled and music_manager.forced_status is None
    return web.json_response({'enabled': live_active})




async def start_web_server(port=8888):
    """Запуск web-сервера для приема статусов"""
    app = web.Application()
    app.router.add_post('/music/update', handle_music_update)
    app.router.add_get('/music/state', handle_get_state)
    
    # Добавляем CORS middleware
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            if request.method == 'OPTIONS':
                response = web.Response()
            else:
                response = await handler(request)
            
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        return middleware_handler

    app.middlewares.append(cors_middleware)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Пробуем разные порты
    ports_to_try = [port, 8889, 8890, 8891]
    
    for current_port in ports_to_try:
        try:
            site = web.TCPSite(runner, '0.0.0.0', current_port)
            await site.start()
            logging.info(f"🌐 Web-сервер для статусов музыки запущен на порту {current_port}")
            return current_port
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logging.warning(f"⚠️ Порт {current_port} занят, пробуем следующий...")
                continue
            else:
                raise e
    
    logging.error("❌ Все порты заняты, не удалось запустить web-сервер")
    return None



async def init_music_manager(client):
    global music_manager
    music_manager = MusicStatusManager(client)
    
    # Загружаем состояние из файла
    saved = load_state(STATE_FILE)
    if saved is not None:
        if saved:
            music_manager.enable()
        else:
            # forced_status сразу выставляем, live выключен
            await music_manager.disable_with_placeholder()
    
    logging.info("✅ MusicManager инициализирован")
    return music_manager



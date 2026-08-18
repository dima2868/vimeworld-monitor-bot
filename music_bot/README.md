# 🎵 Standalone Discord Music Bot

Выделенный независимый Discord-бот для музыки и плейлистов (YouTube, Spotify, SoundCloud, YouTube Music, MC ПОХ).

## 🚀 Возможности
- **Spotify**: Плейлисты, альбомы, треки (включая ссылки `intl-xx` и `spotify.link`).
- **YouTube & YouTube Music**: Плейлисты, альбомы, одиночные видео и радио-миксы.
- **SoundCloud**: Прямой стриминг треков и мобильных коротких ссылок `on.soundcloud.com`.
- **MC ПОХ**: Полная локальная оффлайн-дискография (20 треков).
- **Интерактивные кнопки**: Пауза / Продолжить, След. трек, Перемешать (Shuffle), Зациклить (Loop), Стоп, Очередь.

## 📋 Слэш-команды
- `/play [query]` — Включить трек, плейлист или альбом
- `/pause` — Поставить на паузу
- `/resume` — Возобновить воспроизведение
- `/skip` — Пропустить трек
- `/stop` — Остановить и отключить бота
- `/queue` — Посмотреть текущую очередь
- `/shuffle` — Перемешать очередь

## ⚙️ Установка и запуск

1. Перейдите в папку `music_bot`:
```bash
cd music_bot
pip install -r requirements.txt
```

2. Создайте файл `.env`:
```env
DISCORD_MUSIC_BOT_TOKEN=your_music_bot_token_here
```

3. Запустите бота:
```bash
python bot.py
```

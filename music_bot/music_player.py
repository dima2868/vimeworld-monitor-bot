import os
import random
import asyncio
import logging
import urllib.parse
import urllib.request
import ssl
import json
import re
import discord
from discord import app_commands
import yt_dlp

logger = logging.getLogger(__name__)

# SSL context for HTTPS requests
ssl_ctx = ssl._create_unverified_context()

# Complete curated discography of MC ПОХ with local file mappings
MC_POH_PLAYLIST = [
    {"title": "МС ПОХ - Банька парилка", "file": "01_banka_parilka.mp4", "query": "МС ПОХ Банька парилка"},
    {"title": "МС ПОХ - Весенний лес", "file": "02_vesenniy_les.mp4", "query": "МС ПОХ Весенний лес"},
    {"title": "МС ПОХ - Школа", "file": "03_shkola.mp4", "query": "МС ПОХ Школа"},
    {"title": "МС ПОХ - Детство", "file": "04_detstvo.mp4", "query": "МС ПОХ Детство"},
    {"title": "МС ПОХ - Ярость", "file": "05_yarost.mp4", "query": "МС ПОХ Ярость"},
    {"title": "МС ПОХ - Онанизм", "file": "06_onanizm.mp4", "query": "МС ПОХ Онанизм"},
    {"title": "МС ПОХ - Дудка", "file": "07_dudka.mp4", "query": "МС ПОХ Дудка"},
    {"title": "МС ПОХ - С.К.У.Ф.", "file": "08_skuf.mp4", "query": "МС ПОХ СКУФ"},
    {"title": "МС ПОХ - Летняя песенка", "file": "09_letnyaya_pesenka.mp4", "query": "МС ПОХ Летняя песенка"},
    {"title": "МС ПОХ - HORADANCE", "file": "10_horadance.mp4", "query": "МС ПОХ HORADANCE"},
    {"title": "МС ПОХ - OLDSCHOOL", "file": "11_oldschool.mp4", "query": "МС ПОХ OLDSCHOOL"},
    {"title": "МС ПОХ - Даченька", "file": "12_dachenka.mp4", "query": "МС ПОХ Даченька"},
    {"title": "МС ПОХ - Свидание", "file": "13_svidanie.mp4", "query": "МС ПОХ Свидание"},
    {"title": "МС ПОХ - Лирика", "file": "14_lirika.mp4", "query": "МС ПОХ Лирика"},
    {"title": "МС ПОХ - Сэй Ма Нэйм", "file": "15_say_my_name.mp4", "query": "МС ПОХ Сэй Ма Нэйм"},
    {"title": "МС ПОХ - Л.К.С.Е.", "file": "16_lkse.mp4", "query": "МС ПОХ ЛКСЕ"},
    {"title": "МС ПОХ - Жирный", "file": "17_zhirniy.mp4", "query": "МС ПОХ Жирный"},
    {"title": "МС ПОХ - Я и Бал", "file": "18_ya_i_bal.mp4", "query": "МС ПОХ Я и Бал"},
    {"title": "МС ПОХ - Гетто", "file": "19_ghetto.mp4", "query": "МС ПОХ Гетто"},
    {"title": "МС ПОХ - Вероника", "file": "20_veronika.mp4", "query": "МС ПОХ Вероника"}
]

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'extractor_args': {
        'youtube': {
            'player_client': ['android_creator', 'android', 'tv_embedded']
        }
    }
}

SC_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch'
}

FFMPEG_STREAM_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af "volume=1.3"'
}

FFMPEG_LOCAL_OPTIONS = {
    'options': '-vn -af "volume=1.3"'
}


def clean_youtube_url(url: str) -> str:
    """Strips tracking, radio mix (RD...) and playlist params to get pure video URL."""
    if 'youtube.com' in url or 'youtu.be' in url:
        parsed = urllib.parse.urlparse(url)
        if 'youtu.be' in parsed.netloc:
            video_id = parsed.path.lstrip('/')
            return f"https://www.youtube.com/watch?v={video_id}"
        qs = urllib.parse.parse_qs(parsed.query)
        if 'v' in qs:
            v_id = qs['v'][0]
            return f"https://www.youtube.com/watch?v={v_id}"
        if 'list' in qs:
            list_id = qs['list'][0]
            return f"https://www.youtube.com/playlist?list={list_id}"
    return url


def get_youtube_metadata_oembed(url: str):
    """Fetches video title, author and thumbnail from public YouTube oEmbed without auth or bot checks."""
    try:
        clean_url = clean_youtube_url(url)
        oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(clean_url)}&format=json"
        req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {
                'title': data.get('title'),
                'author': data.get('author_name'),
                'thumbnail': data.get('thumbnail_url'),
                'webpage_url': clean_url
            }
    except Exception:
        return None


def get_spotify_info(url: str):
    """Extracts track, playlist or album metadata from Spotify links (including intl-xx, mobile shortlinks and URIs)."""
    # 1. Spotify URI support (spotify:track:xxx, spotify:playlist:xxx, spotify:album:xxx)
    uri_match = re.search(r'spotify:(track|playlist|album):([a-zA-Z0-9]+)', url)
    if uri_match:
        item_type, item_id = uri_match.group(1), uri_match.group(2)
        url = f"https://open.spotify.com/{item_type}/{item_id}"

    # 2. Mobile shortlinks (spotify.link / spoti.fi)
    if 'spotify.link' in url or 'spoti.fi' in url:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                url = resp.geturl()
        except Exception as e:
            logger.debug(f"spotify.link resolution error: {e}")

    # 3. Match track, playlist, or album with optional intl-xx prefix
    m = re.search(r'spotify\.com/(?:intl-[a-z]+/)?(track|playlist|album)/([a-zA-Z0-9]+)', url)
    if not m:
        return None
    item_type, item_id = m.group(1), m.group(2)

    # 4. Single Track
    if item_type == 'track':
        oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{item_id}"
        try:
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                title = data.get('title')
                author = data.get('author_name')
                full_name = f"{author} - {title}" if author and author not in title else title
                return {
                    'is_playlist': False,
                    'title': full_name,
                    'tracks': [{'title': full_name, 'query': full_name, 'thumbnail': data.get('thumbnail_url'), 'uploader': author or 'Spotify'}],
                    'source': 'spotify'
                }
        except Exception:
            pass

    # 5. Embed page for Playlist or Album
    embed_url = f"https://open.spotify.com/embed/{item_type}/{item_id}"
    try:
        req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            html = resp.read().decode('utf-8')
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                playlist_title = entity.get('title') or entity.get('name') or "Spotify Playlist"
                raw_tracklist = entity.get('trackList', [])
                tracks = []
                for item in raw_tracklist:
                    t_title = item.get('title')
                    t_artist = item.get('subtitle')
                    full_name = f"{t_artist} - {t_title}" if t_artist else t_title
                    tracks.append({
                        'title': full_name,
                        'query': full_name,
                        'duration': int(item.get('duration', 0) / 1000),
                        'uploader': t_artist or 'Spotify'
                    })
                if tracks:
                    return {'is_playlist': True, 'title': playlist_title, 'tracks': tracks, 'source': 'spotify'}

            res_match = re.search(r'<script id="resource"[^>]*>(\{.*?\})</script>', html, re.DOTALL)
            if res_match:
                data = json.loads(res_match.group(1))
                playlist_title = data.get('name', 'Spotify Playlist')
                track_items = data.get('tracks', {}).get('items', [])
                tracks = []
                for item in track_items:
                    t = item.get('track', item)
                    t_title = t.get('name')
                    artists = [a.get('name') for a in t.get('artists', []) if a.get('name')]
                    artist_str = ", ".join(artists) if artists else ""
                    full_name = f"{artist_str} - {t_title}" if artist_str else t_title
                    tracks.append({
                        'title': full_name,
                        'query': full_name,
                        'duration': int(t.get('duration_ms', 0) / 1000),
                        'uploader': artist_str or 'Spotify'
                    })
                if tracks:
                    return {'is_playlist': True, 'title': playlist_title, 'tracks': tracks, 'source': 'spotify'}
    except Exception:
        pass
    return None


def get_yt_playlist_info(url: str):
    """Extracts tracklist from YouTube / YouTube Music playlists (including watch?v=...&list=PL...)."""
    if 'list=' in url:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        if 'list' in qs:
            list_id = qs['list'][0]
            url = f"https://www.youtube.com/playlist?list={list_id}"

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and info['entries']:
                pl_title = info.get('title', 'YouTube Playlist')
                tracks = []
                for entry in info['entries']:
                    if not entry:
                        continue
                    t_title = entry.get('title')
                    if not t_title or '[Private video]' in t_title or '[Deleted video]' in t_title:
                        continue
                    t_url = entry.get('url') or (f"https://www.youtube.com/watch?v={entry.get('id')}" if entry.get('id') else None)
                    if not t_url:
                        continue
                    tracks.append({
                        'title': t_title,
                        'query': t_url,
                        'url': t_url,
                        'duration': entry.get('duration', 0),
                        'uploader': entry.get('uploader') or entry.get('channel', 'YouTube')
                    })
                if tracks:
                    return {'is_playlist': True, 'title': pl_title, 'tracks': tracks, 'source': 'youtube_playlist'}
        except Exception:
            pass
    return None


def clean_music_query(query: str) -> str:
    """Cleans URLs, prefixes and share text boilerplate (SoundCloud, YouTube, Spotify)."""
    if not query:
        return ""
    q = query.strip()
    q = re.sub(r'^(scsearch:|ytsearch:)+', '', q, flags=re.IGNORECASE).strip()

    # Strip SoundCloud share text: 'Listen to X by Y on #SoundCloud' or 'Stream X by Y...'
    m = re.search(r'(?:Listen to|Stream)\s+(.*?)\s+by\s+(.*?)(?:\s+on\s+.*|\s+https?:.*|$)', q, re.IGNORECASE)
    if m:
        track_name = m.group(1).strip()
        artist = m.group(2).strip()
        artist = re.sub(r'\s+on\b.*$', '', artist, flags=re.IGNORECASE).strip()
        return f"{artist} - {track_name}"

    if 'soundcloud.com' in q:
        if 'on.soundcloud.com' in q:
            try:
                req = urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=4, context=ssl_ctx) as resp:
                    q = resp.geturl()
            except Exception:
                pass
        parsed = urllib.parse.urlparse(q)
        path = parsed.path.strip('/')
        parts = [p.replace('-', ' ') for p in path.split('/') if p and p not in ('sets', 'tracks', 'discover')]
        if len(parts) >= 2:
            return f"{parts[0]} - {parts[1]}"
        elif len(parts) == 1:
            return parts[0]

    return q


def is_youtube_playlist_url(url: str) -> bool:
    """Checks if URL is a YouTube or YouTube Music playlist."""
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return False
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)

    if '/playlist' in parsed.path or '/browse/VL' in parsed.path:
        return True

    if 'list' in qs:
        if 'v' not in qs:
            return True
        list_id = qs['list'][0]
        if list_id.startswith('PL') or list_id.startswith('OLAK') or list_id.startswith('CL') or list_id.startswith('RDCL'):
            return True
    return False


def resolve_query_input(query: str = None) -> dict:
    """
    Universal resolver for all inputs:
    - None -> MC POH Discography
    - Spotify Playlist / Album / Track
    - YouTube Playlist / YouTube Music Playlist (all list formats)
    - SoundCloud URLs / Share text
    - YouTube / YouTube Music video URLs
    - MC POH numbers / names
    - Text search queries
    """
    if not query:
        return {
            'is_playlist': True,
            'title': 'MC ПОХ (Полная дискография)',
            'tracks': list(MC_POH_PLAYLIST),
            'source': 'mc_poh'
        }

    q = query.strip()

    # 1. Spotify
    if 'spotify.com' in q or 'spotify.link' in q or 'spoti.fi' in q or q.startswith('spotify:'):
        res = get_spotify_info(q)
        if res:
            return res

    # 2. YouTube / YouTube Music Playlist
    if is_youtube_playlist_url(q):
        res = get_yt_playlist_info(q)
        if res:
            return res

    # 3. SoundCloud / Share text
    cleaned_sc = clean_music_query(q)
    if 'soundcloud.com' in q or re.search(r'(?:Listen to|Stream)\s+', q, re.IGNORECASE):
        return {
            'is_playlist': False,
            'title': cleaned_sc,
            'tracks': [{'title': cleaned_sc, 'query': cleaned_sc, 'uploader': 'SoundCloud'}],
            'source': 'soundcloud'
        }

    # 4. MC POH track number (1-20)
    if q.isdigit():
        num = int(q)
        if 1 <= num <= len(MC_POH_PLAYLIST):
            track = MC_POH_PLAYLIST[num - 1]
            return {
                'is_playlist': False,
                'title': track['title'],
                'tracks': [track],
                'source': 'mc_poh'
            }

    # 5. MC POH track name match
    for t in MC_POH_PLAYLIST:
        if q.lower() in t['title'].lower():
            return {
                'is_playlist': False,
                'title': t['title'],
                'tracks': [t],
                'source': 'mc_poh'
            }

    # 6. YouTube Single Track / Search
    clean_q = clean_youtube_url(q)
    return {
        'is_playlist': False,
        'title': clean_q,
        'tracks': [{'title': clean_q, 'query': clean_q, 'uploader': 'Онлайн'}],
        'source': 'single'
    }


def generate_search_candidates(query: str) -> list[str]:
    """Generates clean variations of artist + title queries (e.g. from Spotify) to maximize search hit rate."""
    candidates = [query]
    if ' - ' in query:
        artist_part, title_part = query.split(' - ', 1)
        clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title_part).strip()
        primary_artist = re.split(r'[,&]|\bfeat\.?\b|\bft\.?\b', artist_part, flags=re.IGNORECASE)[0].strip()
        
        candidates.append(f"{primary_artist} {clean_title}")
        candidates.append(f"{primary_artist} {title_part}")
        candidates.append(clean_title)
        candidates.append(title_part)
        
        artists = [a.strip() for a in re.split(r'[,&]', artist_part) if a.strip()]
        if len(artists) > 1:
            candidates.append(f"{artists[1]} {clean_title}")

    seen = set()
    result = []
    for c in candidates:
        c_clean = c.strip()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            result.append(c_clean)
    return result


def extract_track_info_sync(query: str):
    """
    Extracts direct audio stream URL and metadata.
    1. Direct audio links (.mp3, .ogg, .wav, .m4a, etc.)
    2. Direct YouTube URL resolution
    3. Multi-candidate search across SoundCloud and YouTube (for Spotify / text queries).
    """
    try:
        # 1. Direct audio link
        direct_extensions = ('.mp3', '.m4a', '.ogg', '.wav', '.aac', '.flac', '.opus')
        if any(query.lower().startswith(p) for p in ('http://', 'https://')) and any(query.lower().split('?')[0].endswith(ext) for ext in direct_extensions):
            filename = query.split('/')[-1].split('?')[0]
            return {
                'title': filename,
                'url': query,
                'webpage_url': query,
                'duration': 0,
                'thumbnail': None,
                'uploader': 'Прямая ссылка'
            }

        clean_query = clean_music_query(query)
        if clean_query.startswith('http://') or clean_query.startswith('https://'):
            clean_query = clean_youtube_url(clean_query)

        is_yt = 'youtube.com' in clean_query or 'youtu.be' in clean_query
        yt_meta = get_youtube_metadata_oembed(clean_query) if is_yt else None

        # 2. If direct YouTube URL, try YouTube first with direct link, then fallback
        if is_yt:
            try:
                with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                    info = ydl.extract_info(clean_query, download=False)
                    if 'entries' in info and info['entries']:
                        info = info['entries'][0]
                    if info and info.get('url'):
                        return {
                            'title': info.get('title') or (yt_meta.get('title') if yt_meta else clean_query),
                            'url': info.get('url'),
                            'webpage_url': info.get('webpage_url', clean_query),
                            'duration': info.get('duration', 0),
                            'thumbnail': info.get('thumbnail') or (yt_meta.get('thumbnail') if yt_meta else None),
                            'uploader': info.get('uploader') or (yt_meta.get('author') if yt_meta else 'YouTube')
                        }
            except Exception as yt_err:
                logger.info(f"Direct YouTube extraction failed ({yt_err}), falling back to search...")

        # 3. Search candidates across SoundCloud and YouTube (for Spotify / text queries)
        search_base = yt_meta['title'] if (is_yt and yt_meta) else clean_query
        candidates = generate_search_candidates(search_base)

        for cand in candidates:
            # Try SoundCloud
            try:
                with yt_dlp.YoutubeDL(SC_OPTIONS) as ydl:
                    sc_info = ydl.extract_info(f"scsearch:{cand}", download=False)
                    if 'entries' in sc_info and sc_info['entries']:
                        entry = sc_info['entries'][0]
                        if entry and entry.get('url'):
                            return {
                                'title': (yt_meta.get('title') if yt_meta else None) or entry.get('title', clean_query),
                                'url': entry.get('url'),
                                'webpage_url': clean_query if is_yt else entry.get('webpage_url', clean_query),
                                'duration': entry.get('duration', 0),
                                'thumbnail': (yt_meta.get('thumbnail') if yt_meta else None) or entry.get('thumbnail'),
                                'uploader': (yt_meta.get('author') if yt_meta else None) or entry.get('uploader', 'SoundCloud')
                            }
            except Exception:
                pass

            # Try YouTube
            try:
                with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                    yt_info = ydl.extract_info(f"ytsearch:{cand}", download=False)
                    if 'entries' in yt_info and yt_info['entries']:
                        entry = yt_info['entries'][0]
                        if entry and entry.get('url'):
                            return {
                                'title': (yt_meta.get('title') if yt_meta else None) or entry.get('title', clean_query),
                                'url': entry.get('url'),
                                'webpage_url': clean_query if is_yt else entry.get('webpage_url', clean_query),
                                'duration': entry.get('duration', 0),
                                'thumbnail': (yt_meta.get('thumbnail') if yt_meta else None) or entry.get('thumbnail'),
                                'uploader': (yt_meta.get('author') if yt_meta else None) or entry.get('uploader', 'YouTube')
                            }
            except Exception:
                pass

        return None
    except Exception as e:
        logger.error(f"Fatal error extracting audio for '{query}': {e}")
        return None


class MusicControlView(discord.ui.View):
    """Interactive Discord UI button controller for the music player."""
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player = player
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()

        # Play / Pause toggle
        pause_label = "▶️ Продолжить" if self.player.is_paused else "⏸️ Пауза"
        btn_pause = discord.ui.Button(
            label=pause_label,
            style=discord.ButtonStyle.primary if not self.player.is_paused else discord.ButtonStyle.secondary,
            custom_id="music_pause_resume"
        )
        btn_pause.callback = self.on_pause_resume
        self.add_item(btn_pause)

        # Skip
        btn_skip = discord.ui.Button(
            label="⏭️ След.",
            style=discord.ButtonStyle.secondary,
            custom_id="music_skip"
        )
        btn_skip.callback = self.on_skip
        self.add_item(btn_skip)

        # Shuffle
        btn_shuffle = discord.ui.Button(
            label=f"🔀 {'ВКЛ' if self.player.is_shuffle else 'ВЫКЛ'}",
            style=discord.ButtonStyle.success if self.player.is_shuffle else discord.ButtonStyle.secondary,
            custom_id="music_shuffle"
        )
        btn_shuffle.callback = self.on_shuffle
        self.add_item(btn_shuffle)

        # Loop
        btn_loop = discord.ui.Button(
            label=f"🔁 {'ВКЛ' if self.player.is_loop else 'ВЫКЛ'}",
            style=discord.ButtonStyle.success if self.player.is_loop else discord.ButtonStyle.secondary,
            custom_id="music_loop"
        )
        btn_loop.callback = self.on_loop
        self.add_item(btn_loop)

        # Stop
        btn_stop = discord.ui.Button(
            label="⏹️ Стоп",
            style=discord.ButtonStyle.danger,
            custom_id="music_stop"
        )
        btn_stop.callback = self.on_stop
        self.add_item(btn_stop)

        # Tracklist
        btn_list = discord.ui.Button(
            label="📜 Очередь",
            style=discord.ButtonStyle.secondary,
            custom_id="music_list"
        )
        btn_list.callback = self.on_list
        self.add_item(btn_list)

    async def on_pause_resume(self, interaction: discord.Interaction):
        if self.player.is_paused or not (self.player.voice_client and self.player.voice_client.is_playing()):
            resumed = await self.player.resume_playback(interaction)
            if resumed:
                await interaction.response.send_message("▶️ Воспроизведение возобновлено.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Очередь пуста. Включите трек через `/play`.", ephemeral=True)
        else:
            self.player.pause()
            await interaction.response.send_message("⏸️ Музыка поставлена на паузу.", ephemeral=True)
        self.update_buttons()
        if self.player.message:
            try:
                await self.player.message.edit(embed=self.player.build_now_playing_embed(), view=self)
            except Exception:
                pass

    async def on_skip(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏭️ Переключаю на следующий трек...", ephemeral=True)
        await self.player.skip()

    async def on_shuffle(self, interaction: discord.Interaction):
        self.player.toggle_shuffle()
        self.update_buttons()
        if self.player.message:
            try:
                await self.player.message.edit(embed=self.player.build_now_playing_embed(), view=self)
            except Exception:
                pass
        await interaction.response.send_message(f"🔀 Перемешивание {'включено' if self.player.is_shuffle else 'выключено'}.", ephemeral=True)

    async def on_loop(self, interaction: discord.Interaction):
        self.player.is_loop = not self.player.is_loop
        self.update_buttons()
        if self.player.message:
            try:
                await self.player.message.edit(embed=self.player.build_now_playing_embed(), view=self)
            except Exception:
                pass
        await interaction.response.send_message(f"🔁 Повтор плейлиста {'включен' if self.player.is_loop else 'выключен'}.", ephemeral=True)

    async def on_stop(self, interaction: discord.Interaction):
        await self.player.stop()
        await interaction.response.send_message("⏹️ Музыка остановлена, бот отключился от канала.", ephemeral=True)

    async def on_list(self, interaction: discord.Interaction):
        embed = self.player.build_playlist_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)


class MusicPlayer:
    """Singleton music player manager for MC ПОХ, YouTube, Spotify, and SoundCloud streaming."""
    def __init__(self):
        self.queue = []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.is_loop = True
        self.is_shuffle = False
        self.now_playing = None
        self.voice_client = None
        self.message = None
        self.text_channel = None
        self.lock = asyncio.Lock()
        self.interrupted_for_alert = False
        self._manual_transition = False
        self._failed_consecutive = 0

    def load_mc_poh_playlist(self, shuffle: bool = False):
        """Loads the full MC ПОХ tracklist into the queue."""
        tracks = list(MC_POH_PLAYLIST)
        if shuffle:
            random.shuffle(tracks)
        self.queue = tracks
        self.current_index = 0

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        if self.is_shuffle and len(self.queue) > 1:
            current_track = self.queue[self.current_index] if self.queue and self.current_index < len(self.queue) else None
            upcoming = [t for i, t in enumerate(self.queue) if i != self.current_index]
            random.shuffle(upcoming)
            if current_track:
                self.queue = [current_track] + upcoming
                self.current_index = 0
            else:
                self.queue = upcoming

    def build_now_playing_embed(self) -> discord.Embed:
        track = self.now_playing or (self.queue[self.current_index] if self.queue and self.current_index < len(self.queue) else None)
        title = track.get("title", "Музыка") if track else "Неизвестный трек"
        uploader = track.get("uploader") if track else None
        
        duration_str = ""
        if track:
            try:
                raw_dur = float(track.get("duration") or 0)
                if raw_dur > 10000:
                    raw_dur = raw_dur / 1000.0
                total_sec = int(raw_dur)
                if total_sec > 0:
                    mins = total_sec // 60
                    secs = total_sec % 60
                    duration_str = f"⏱ **Длительность:** `{mins}:{secs:02d}`\n"
            except Exception:
                duration_str = ""

        uploader_str = f"👤 **Автор / Источник:** `{uploader}`\n" if uploader else ""
        webpage_url = track.get("webpage_url") if track else None
        link_str = f"🔗 [Ссылка на трек]({webpage_url})\n" if webpage_url and webpage_url.startswith("http") else ""

        status_icon = "⏸️ Пауза" if self.is_paused else "▶️ Играет"
        loop_str = "🟢 ВКЛ" if self.is_loop else "🔴 ВЫКЛ"
        shuffle_str = "🟢 ВКЛ" if self.is_shuffle else "🔴 ВЫКЛ"

        embed = discord.Embed(
            title="🎵 Музыкальный Плеер Discord",
            description=(
                f"### 🎤 `{title}`\n\n"
                f"{uploader_str}"
                f"{duration_str}"
                f"{link_str}"
            ),
            color=0xFF4500
        )
        embed.add_field(name="📊 Статус", value=f"`{status_icon}`", inline=True)
        embed.add_field(name="🔢 Трек в очереди", value=f"`{self.current_index + 1} / {len(self.queue)}`", inline=True)
        embed.add_field(name="🔁 Зацикливание", value=f"`{loop_str}`", inline=True)
        embed.add_field(name="🔀 Перемешивание", value=f"`{shuffle_str}`", inline=True)

        if len(self.queue) > self.current_index + 1:
            next_track = self.queue[self.current_index + 1]["title"]
            embed.add_field(name="⏭️ Следующий трек", value=f"`{next_track}`", inline=False)
        elif self.is_loop and len(self.queue) > 0:
            next_track = self.queue[0]["title"]
            embed.add_field(name="⏭️ Следующий трек (по кругу)", value=f"`{next_track}`", inline=False)

        embed.set_footer(text="Управляйте воспроизведением кнопками ниже или командами /play, /pause, /skip, /stop")
        if track and track.get("thumbnail"):
            embed.set_thumbnail(url=track["thumbnail"])
        return embed

    def build_playlist_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📜 Текущая Очередь Воспроизведения",
            description=f"Всего треков в очереди: **{len(self.queue)}**",
            color=0xF1C40F
        )
        lines = []
        for idx, item in enumerate(self.queue):
            marker = "👉 **" if idx == self.current_index else ""
            end_marker = "** ⬅️ *(играет)*" if idx == self.current_index else ""
            lines.append(f"{marker}{idx + 1}. {item['title']}{end_marker}")

        shown_lines = lines[:25]
        if len(lines) > 25:
            shown_lines.append(f"... и ещё {len(lines) - 25} треков")

        embed.add_field(name="🎵 Список треков", value="\n".join(shown_lines) if shown_lines else "Очередь пуста", inline=False)
        embed.set_footer(text=f"Автоматическое непрерывное воспроизведение")
        return embed

    async def start_playback(self, voice_client: discord.VoiceClient, text_channel=None):
        """Starts or continues playback from current index."""
        self.voice_client = voice_client
        if text_channel:
            self.text_channel = text_channel
            
        self.is_playing = True
        self.is_paused = False
        await self._play_current_track()

    async def _play_current_track(self):
        if not self.queue or self.current_index >= len(self.queue):
            if self.is_loop and self.queue:
                self.current_index = 0
            else:
                await self.stop()
                return

        track_item = self.queue[self.current_index]
        local_filename = track_item.get("file")
        local_path = os.path.join(os.path.dirname(__file__), "sounds", "mcpoh", local_filename) if local_filename else None

        # Check if local file exists (Offline playback for MC POH)
        if local_path and os.path.exists(local_path):
            audio_source = discord.FFmpegPCMAudio(local_path, options=FFMPEG_LOCAL_OPTIONS['options'])
            self.now_playing = {
                "title": track_item.get("title", local_filename),
                "thumbnail": None,
                "duration": 0,
                "uploader": "MC ПОХ (Локальный файл)"
            }
        else:
            # Online stream via URL / YouTube / Spotify / SoundCloud
            query = track_item.get("query", track_item.get("title"))
            track_info = await asyncio.to_thread(extract_track_info_sync, query)
            if not track_info or not track_info.get("url"):
                logger.warning(f"Could not load audio for '{query}', skipping to next...")
                self._failed_consecutive += 1
                if self._failed_consecutive >= min(len(self.queue), 3):
                    logger.error("Too many consecutive track loading failures, stopping playback.")
                    self._failed_consecutive = 0
                    if self.text_channel:
                        try:
                            embed = discord.Embed(
                                title="❌ Не удалось воспроизвести трек",
                                description=f"Не удалось получить аудиопоток для: `{query}`.\nПопробуйте другую ссылку или поисковый запрос.",
                                color=0xE74C3C
                            )
                            await self.text_channel.send(embed=embed)
                        except Exception:
                            pass
                    await self.stop()
                    return
                self.current_index += 1
                await self._play_current_track()
                return

            self._failed_consecutive = 0

            self.now_playing = {
                "title": track_info.get("title", track_item.get("title", query)),
                "url": track_info["url"],
                "webpage_url": track_info.get("webpage_url"),
                "duration": track_info.get("duration", track_item.get("duration", 0)),
                "thumbnail": track_info.get("thumbnail") or track_item.get("thumbnail"),
                "uploader": track_info.get("uploader") or track_item.get("uploader", "Онлайн")
            }
            audio_source = discord.FFmpegPCMAudio(
                track_info["url"],
                before_options=FFMPEG_STREAM_OPTIONS['before_options'],
                options=FFMPEG_STREAM_OPTIONS['options']
            )

        if not self.voice_client or not self.voice_client.is_connected():
            logger.warning("Voice client is not connected for music playback.")
            self.is_playing = False
            return

        # Safely stop existing audio without triggering recursive after callback
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self._manual_transition = True
            self.voice_client.stop()
            await asyncio.sleep(0.05)
            self._manual_transition = False

        try:
            def after_playback(error):
                if error:
                    logger.error(f"Error during audio playback: {error}")
                if self._manual_transition or self.interrupted_for_alert:
                    return
                # Schedule next track in asyncio event loop only when track finishes naturally
                if self.voice_client and self.voice_client.loop:
                    asyncio.run_coroutine_threadsafe(self._on_track_finished(), self.voice_client.loop)

            self.voice_client.play(audio_source, after=after_playback)
            self.is_playing = True
            self.is_paused = False
            logger.info(f"Now playing music track: {self.now_playing['title']}")

            # Send or update Embed in channel
            if self.text_channel:
                embed = self.build_now_playing_embed()
                view = MusicControlView(self)
                if self.message:
                    try:
                        await self.message.edit(embed=embed, view=view)
                    except Exception:
                        self.message = await self.text_channel.send(embed=embed, view=view)
                else:
                    self.message = await self.text_channel.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error starting audio for '{self.now_playing['title']}': {e}")
            self.current_index += 1
            await self._play_current_track()

    async def _on_track_finished(self):
        if not self.is_playing or self._manual_transition:
            return
        self.current_index += 1
        if self.current_index >= len(self.queue):
            if self.is_loop:
                self.current_index = 0
                if self.is_shuffle:
                    random.shuffle(self.queue)
            else:
                await self.stop()
                return
        await self._play_current_track()

    def pause(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True

    def resume(self):
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False

    async def resume_playback(self, interaction: discord.Interaction = None) -> bool:
        """Resumes paused voice stream or restarts playback from current track."""
        if self.voice_client and self.voice_client.is_connected():
            if self.voice_client.is_paused():
                self.voice_client.resume()
                self.is_paused = False
                self.is_playing = True
                return True
            elif not self.voice_client.is_playing() and self.queue:
                self.is_paused = False
                self.is_playing = True
                await self._play_current_track()
                return True
        elif self.queue:
            target_vc = interaction.user.voice.channel if (interaction and interaction.user and interaction.user.voice) else None
            if target_vc:
                self.voice_client = await target_vc.connect()
                self.is_paused = False
                self.is_playing = True
                await self._play_current_track()
                return True
        return False

    async def skip(self):
        if not self.voice_client or not self.is_playing:
            return
        self._manual_transition = True
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
        await asyncio.sleep(0.05)
        self._manual_transition = False

        self.current_index += 1
        if self.current_index >= len(self.queue):
            if self.is_loop:
                self.current_index = 0
            else:
                await self.stop()
                return
        await self._play_current_track()

    async def stop(self):
        self.is_playing = False
        self.is_paused = False
        self.now_playing = None
        self._manual_transition = True
        if self.voice_client and self.voice_client.is_connected():
            if self.voice_client.is_playing() or self.voice_client.is_paused():
                self.voice_client.stop()
            try:
                await self.voice_client.disconnect()
            except Exception:
                pass
            self.voice_client = None
        self._manual_transition = False

        if self.message:
            try:
                embed = discord.Embed(
                    title="⏹️ Воспроизведение остановлено",
                    description="Бот отключился от голосового канала. Включить музыку: `/play`",
                    color=0x95A5A6
                )
                await self.message.edit(embed=embed, view=None)
            except Exception:
                pass
            self.message = None

# Global music player instance
music_player = MusicPlayer()

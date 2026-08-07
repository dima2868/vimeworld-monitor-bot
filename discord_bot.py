import os
import asyncio
import logging
from config import DISCORD_BOT_TOKEN, DISCORD_ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

# Discord client & command tree placeholder
discord_client = None
voice_client = None
tree = None

try:
    import discord
    from discord import app_commands
    from discord.ext import commands
    
    # Use standard non-privileged intents for voice channels and guilds
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    
    discord_client = commands.Bot(command_prefix="!", intents=intents)
    tree = discord_client.tree

    @discord_client.event
    async def on_ready():
        logger.info(f"Discord Bot connected as {discord_client.user} (ID: {discord_client.user.id})")
        try:
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} Discord slash commands.")
        except Exception as e:
            logger.error(f"Error syncing Discord slash commands: {e}")

except ImportError:
    logger.warning("discord.py is not installed. Discord voice notifications will be disabled.")
    discord_client = None


def is_discord_ready() -> bool:
    """Checks if Discord bot is initialized and logged in."""
    return bool(discord_client and discord_client.is_ready())


async def find_active_human_voice_channel():
    """
    Finds a voice channel across all connected Discord servers (guilds)
    that has at least 1 non-bot human member inside.
    """
    if not is_discord_ready():
        return None
        
    for guild in discord_client.guilds:
        for vc in guild.voice_channels:
            human_members = [m for m in vc.members if not m.bot]
            if len(human_members) > 0:
                return vc

    return None


async def get_discord_debug_info() -> str:
    """Returns human-readable status of Discord bot connection."""
    if not DISCORD_BOT_TOKEN:
        return "❌ <b>Токен DISCORD_BOT_TOKEN не указан</b> в переменных окружения."
        
    if not is_discord_ready():
        return "⏳ <b>Discord-бот в процессе подключения...</b> Попробуйте через 5 секунд."
        
    guilds = discord_client.guilds
    if not guilds:
        return (
            "⚠️ <b>Бот подключен к Discord, но НЕ добавлен ни на один сервер!</b>\n\n"
            "Добавьте бота на ваш Discord-сервер по ссылке авторизации."
        )
        
    text = f"✅ <b>Discord-бот активен:</b> <code>{discord_client.user}</code>\n"
    text += f"🏠 <b>Серверы ({len(guilds)}):</b> " + ", ".join([g.name for g in guilds]) + "\n\n"
    
    active_vc = await find_active_human_voice_channel()
    if active_vc:
        humans = [m.display_name for m in active_vc.members if not m.bot]
        text += f"🔊 <b>Найден активный войс:</b> {active_vc.name} (Людей: {len(humans)} - {', '.join(humans)})\n"
    else:
        text += "🔇 <b>Никого нет в голосовых каналах.</b> Зайдите в любой голосовой канал на сервере для теста!\n"
        
    return text


# --- DISCORD UI ADMIN PANEL VIEW ---

class DiscordAdminView(discord.ui.View):
    def __init__(self, admin_id: int, settings: dict):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.settings = settings
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # 1. Hard Dungeon
        hard_on = self.settings.get("sound_dungeon_hard", 1)
        btn_hard = discord.ui.Button(
            label=f"🗡 Сложное: {'🟢 ВКЛ' if hard_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if hard_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_hard"
        )
        btn_hard.callback = self.make_toggle_callback("sound_dungeon_hard")
        self.add_item(btn_hard)

        # 2. Medium Dungeon
        med_on = self.settings.get("sound_dungeon_medium", 1)
        btn_med = discord.ui.Button(
            label=f"⚔️ Среднее: {'🟢 ВКЛ' if med_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if med_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_medium"
        )
        btn_med.callback = self.make_toggle_callback("sound_dungeon_medium")
        self.add_item(btn_med)

        # 3. Jeju Raid
        jeju_on = self.settings.get("sound_dungeon_jeju", 1)
        btn_jeju = discord.ui.Button(
            label=f"🌋 Чеджу: {'🟢 ВКЛ' if jeju_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if jeju_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_jeju"
        )
        btn_jeju.callback = self.make_toggle_callback("sound_dungeon_jeju")
        self.add_item(btn_jeju)

        # 4. Lololoshka
        lol_on = self.settings.get("sound_MrLalalashkaXXL", 1)
        btn_lol = discord.ui.Button(
            label=f"🎬 Лололошка: {'🟢 ВКЛ' if lol_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if lol_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_MrLalalashkaXXL"
        )
        btn_lol.callback = self.make_toggle_callback("sound_MrLalalashkaXXL")
        self.add_item(btn_lol)

        # 5. FixPlay
        fix_on = self.settings.get("sound_F1xPlay_", 1)
        btn_fix = discord.ui.Button(
            label=f"🎮 Фиксплей: {'🟢 ВКЛ' if fix_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if fix_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_F1xPlay_"
        )
        btn_fix.callback = self.make_toggle_callback("sound_F1xPlay_")
        self.add_item(btn_fix)

    def make_toggle_callback(self, key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.admin_id:
                await interaction.response.send_message("⛔ У вас нет доступа к этой панели управления.", ephemeral=True)
                return
                
            current_val = self.settings.get(key, 1)
            new_val = 0 if current_val else 1
            await db.set_discord_setting(key, new_val)
            self.settings[key] = new_val
            
            self.update_buttons()
            embed = generate_admin_embed(self.settings)
            await interaction.response.edit_message(embed=embed, view=self)
            
        return callback


def generate_admin_embed(settings: dict) -> discord.Embed:
    embed = discord.Embed(
        title="👑 Панель Управления Голосовыми Анонсами Discord",
        description="Здесь вы можете включать или выключать отдельные голосовые озвучки для сервера:",
        color=0x5865F2
    )
    embed.add_field(name="🗡 Сложное подземелье", value="🟢 Включено" if settings.get("sound_dungeon_hard", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="⚔️ Среднее подземелье", value="🟢 Включено" if settings.get("sound_dungeon_medium", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🌋 Остров Чеджу (18:00)", value="🟢 Включено" if settings.get("sound_dungeon_jeju", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🎬 Лололошка", value="🟢 Включено" if settings.get("sound_MrLalalashkaXXL", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🎮 Фиксплей", value="🟢 Включено" if settings.get("sound_F1xPlay_", 1) else "🔴 Выключено", inline=True)
    embed.set_footer(text="Нажимайте на кнопки ниже для переключения статуса")
    return embed


# Register Discord Slash Command /admin
if tree:
    @tree.command(name="admin", description="Админ-панель настройки голосовых уведомлений (только для администратора)")
    async def slash_admin(interaction: discord.Interaction):
        # Strict Admin User ID check
        if interaction.user.id not in DISCORD_ADMIN_IDS:
            await interaction.response.send_message("⛔ **У вас нет доступа к этой админ-панели.**", ephemeral=True)
            return
            
        settings = await db.get_all_discord_settings()
        embed = generate_admin_embed(settings)
        view = DiscordAdminView(admin_id=interaction.user.id, settings=settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def play_voice_sound(sound_filename: str) -> tuple[bool, str]:
    """
    Plays an MP3/OGG sound file in the active Discord Voice Channel ONLY IF:
    1. At least 1 human is inside a voice channel.
    2. The setting for this sound is enabled by the admin.
    """
    global voice_client
    if not DISCORD_BOT_TOKEN:
        return False, "❌ Токен DISCORD_BOT_TOKEN не установлен в переменных окружения!"

    if not is_discord_ready():
        return False, "⏳ Discord бот еще не подключился к сетям Discord. Подождите пару секунд."

    # Map sound filenames to setting keys
    setting_key = None
    if sound_filename == "dungeon_hard.mp3":
        setting_key = "sound_dungeon_hard"
    elif sound_filename == "dungeon_medium.mp3":
        setting_key = "sound_dungeon_medium"
    elif sound_filename == "jeju_raid.mp3":
        setting_key = "sound_dungeon_jeju"
    elif sound_filename == "lololoshka_online.mp3":
        setting_key = "sound_MrLalalashkaXXL"
    elif sound_filename == "fixplay_online.mp3":
        setting_key = "sound_F1xPlay_"

    # Check setting status if key mapped
    if setting_key:
        is_enabled = await db.get_discord_setting(setting_key, 1)
        if not is_enabled:
            msg = f"⏸ Звуковое уведомление '{sound_filename}' отключено администратором в Discord /admin."
            logger.info(msg)
            return False, msg

    # Check if any voice channel has active human members
    target_vc = await find_active_human_voice_channel()
    if not target_vc:
        msg = "🔇 Ни один человек не найден ни в одном голосовом канале! Зайдите в любой войс-канал на сервере и повторите тест."
        logger.info(f"Skipping Discord voice alert '{sound_filename}': {msg}")
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect()
            except Exception:
                pass
            voice_client = None
        return False, msg
        
    sound_path = os.path.join("sounds", sound_filename)
    if not os.path.exists(sound_path):
        sound_path = sound_filename # Fallback to root dir
        
    if not os.path.exists(sound_path):
        msg = f"❌ Файл звука '{sound_filename}' не найден на сервере!"
        logger.warning(msg)
        return False, msg

    try:
        # Connect or move to the channel with human members
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != target_vc.id:
                await voice_client.move_to(target_vc)
        else:
            voice_client = await target_vc.connect()
            
        logger.info(f"Connected to Discord Voice Channel '{target_vc.name}' with human members.")

        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()
                
            # FFmpeg option: -af "volume=4.0" amplifies audio volume to 400% (+12 dB)
            audio_source = discord.FFmpegPCMAudio(sound_path, options='-af "volume=4.0"')
            voice_client.play(audio_source)
            logger.info(f"Playing Discord voice alert (+400% volume): {sound_filename} in channel '{target_vc.name}'")
            
            # Background task to disconnect cleanly as soon as audio finishes playing
            async def disconnect_after_playback():
                global voice_client
                try:
                    while voice_client and voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(1)
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect()
                        voice_client = None
                        logger.info(f"Disconnected from Discord voice channel after playing {sound_filename}.")
                except Exception as ex:
                    logger.warning(f"Error disconnecting after playback: {ex}")
                    voice_client = None

            asyncio.create_task(disconnect_after_playback())
            
            return True, f"🔊 Проигрываю звук <b>{sound_filename}</b> в канале <b>{target_vc.name}</b>!"
    except Exception as e:
        err_msg = f"❌ Ошибка воспроизведения звука: {e}"
        logger.error(err_msg)
        return False, err_msg


async def start_discord_bot():
    """Launches Discord bot in background if DISCORD_BOT_TOKEN is set."""
    if not DISCORD_BOT_TOKEN:
        logger.info("DISCORD_BOT_TOKEN is not set. Discord voice bot skipped.")
        return
        
    if discord_client:
        logger.info("Starting Discord Voice Bot...")
        try:
            await discord_client.start(DISCORD_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Error running Discord bot: {e}")

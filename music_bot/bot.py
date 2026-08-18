import os
import asyncio
import logging
import discord
from discord import app_commands
from config import DISCORD_MUSIC_BOT_TOKEN, EXCLUDED_VOICE_CHANNEL_IDS, DISCORD_ADMIN_IDS
from music_player import music_player, MC_POH_PLAYLIST, resolve_query_input

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MusicBot")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
voice_client = None


async def find_active_human_voice_channel(guild: discord.Guild = None):
    """Finds first active voice channel with human members."""
    guilds = [guild] if guild else client.guilds
    for g in guilds:
        if not g:
            continue
        for vc in g.voice_channels:
            if vc.id in EXCLUDED_VOICE_CHANNEL_IDS or (g.afk_channel and vc.id == g.afk_channel.id):
                continue
            humans = [m for m in vc.members if not m.bot]
            if humans:
                return vc
    return None


@client.event
async def on_ready():
    logger.info(f"🎶 Discord Music Bot logged in as {client.user} (ID: {client.user.id})")
    try:
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} music slash commands globally.")
        for g in client.guilds:
            try:
                tree.copy_global_to(guild=g)
                await tree.sync(guild=g)
                logger.info(f"Synced commands to guild: {g.name} ({g.id})")
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")

    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/play | YouTube, Spotify, MC ПОХ"
        )
    )


@tree.command(name="play", description="Включить музыку: YouTube, Spotify, SoundCloud, YouTube Music, MC ПОХ")
@app_commands.describe(query="Ссылка (YouTube / Spotify / SoundCloud), название трека/плейлиста или номер трека MC ПОХ")
async def slash_play(interaction: discord.Interaction, query: str = None):
    await interaction.response.defer(ephemeral=False)
    
    # 1. Determine target voice channel
    target_vc = interaction.user.voice.channel if (interaction.user and interaction.user.voice) else None
    if not target_vc:
        target_vc = await find_active_human_voice_channel(interaction.guild)
        
    if not target_vc:
        await interaction.followup.send("❌ **Зайдите в голосовой канал**, чтобы включить музыку!", ephemeral=True)
        return

    if target_vc.id in EXCLUDED_VOICE_CHANNEL_IDS or (interaction.guild.afk_channel and target_vc.id == interaction.guild.afk_channel.id):
        await interaction.followup.send("❌ Нельзя воспроизводить музыку в **AFK канале** или **Гостиной 2**!", ephemeral=True)
        return

    global voice_client
    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != target_vc.id:
                await voice_client.move_to(target_vc)
        else:
            voice_client = await target_vc.connect()
    except Exception as e:
        await interaction.followup.send(f"❌ Не удалось подключиться к голосовому каналу: {e}", ephemeral=True)
        return

    # 2. Resolve input in background thread
    res = await asyncio.to_thread(resolve_query_input, query)
    if not res or not res.get("tracks"):
        await interaction.followup.send(f"❌ Не удалось найти или загрузить треки по запросу: `{query}`", ephemeral=True)
        return

    tracks = res["tracks"]
    is_pl = res.get("is_playlist", False)
    title = res.get("title", query or "Плейлист")
    source = res.get("source", "single")

    if is_pl:
        # Full playlist replacement
        music_player.queue = list(tracks)
        music_player.current_index = 0
        
        source_icon = "🟢 Spotify" if source == "spotify" else ("🔴 YouTube" if source == "youtube_playlist" else "🔥 MC ПОХ")
        embed = discord.Embed(
            title=f"📥 Загружен плейлист: {title}",
            description=(
                f"🏷 **Источник:** `{source_icon}`\n"
                f"🔢 **Всего треков:** `{len(tracks)}`\n"
                f"▶️ **Запуск первого трека:** `{tracks[0]['title']}`"
            ),
            color=0x2ECC71
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        await music_player.start_playback(voice_client, interaction.channel)
    else:
        # Single track
        single_track = tracks[0]
        if music_player.is_playing and voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            music_player.queue.append(single_track)
            pos = len(music_player.queue)
            embed = discord.Embed(
                title="➕ Трек добавлен в очередь",
                description=f"🎵 **Трек:** `{single_track['title']}`\n🔢 **Позиция в очереди:** `#{pos}`",
                color=0x3498DB
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            music_player.queue = [single_track]
            music_player.current_index = 0
            await interaction.followup.send(f"▶️ **Запускаю:** `{single_track['title']}`...", ephemeral=False)
            await music_player.start_playback(voice_client, interaction.channel)


@tree.command(name="pause", description="Поставить музыку на паузу")
async def slash_pause(interaction: discord.Interaction):
    if not music_player.is_playing:
        await interaction.response.send_message("❌ Сейчас ничего не играет.", ephemeral=True)
        return
    music_player.pause()
    await interaction.response.send_message("⏸️ Музыка поставлена на паузу.", ephemeral=False)


@tree.command(name="resume", description="Продолжить воспроизведение музыки")
async def slash_resume(interaction: discord.Interaction):
    resumed = await music_player.resume_playback(interaction)
    if resumed:
        await interaction.response.send_message("▶️ Воспроизведение возобновлено.", ephemeral=False)
    else:
        await interaction.response.send_message("❌ Сейчас ничего не играет и очередь пуста. Включите трек через `/play`.", ephemeral=True)


@tree.command(name="skip", description="Переключить на следующий трек")
async def slash_skip(interaction: discord.Interaction):
    if not music_player.is_playing:
        await interaction.response.send_message("❌ Сейчас ничего не играет.", ephemeral=True)
        return
    await interaction.response.send_message("⏭️ Переключаю на следующий трек...", ephemeral=False)
    await music_player.skip()


@tree.command(name="stop", description="Остановить воспроизведение и отключить бота")
async def slash_stop(interaction: discord.Interaction):
    await music_player.stop()
    await interaction.response.send_message("⏹️ Музыка остановлена, бот отключился от канала.", ephemeral=False)


@tree.command(name="queue", description="Показать текущую очередь воспроизведения")
async def slash_queue(interaction: discord.Interaction):
    embed = music_player.build_playlist_embed()
    await interaction.response.send_message(embed=embed, ephemeral=False)


@tree.command(name="shuffle", description="Перемешать очередь треков")
async def slash_shuffle(interaction: discord.Interaction):
    music_player.toggle_shuffle()
    status_str = "включено" if music_player.is_shuffle else "выключено"
    await interaction.response.send_message(f"🔀 Перемешивание очереди **{status_str}**.", ephemeral=False)


def main():
    if not DISCORD_MUSIC_BOT_TOKEN:
        logger.error("❌ DISCORD_MUSIC_BOT_TOKEN (or DISCORD_BOT_TOKEN) is not set in environment or config.py!")
        return
    client.run(DISCORD_MUSIC_BOT_TOKEN)


if __name__ == "__main__":
    main()

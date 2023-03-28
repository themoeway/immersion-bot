import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import sys
from typing import Optional
from discord.app_commands import Choice
from db import Store
from common import emoji
from datetime import date as new_date, datetime, timedelta

db_name = "logs.db"

class Helpers:
    def _media_type_counter(media_type):
        if media_type == "BOOK":
            return 'pgs'
        elif media_type == "MANGA":
            return 'pgs'
        elif media_type == "VN":
            return 'chars'
        elif media_type == "ANIME":
            return 'eps'
        elif media_type == "LISTENING":
            return 'mins'
        elif media_type == "READTIME":
            return 'mins'
        elif media_type == "READING":
            return 'chars'
        else:
            raise Exception(f'Unknown media type: {media_type}')

    def media_type_converter_help(media_type):
        if media_type == "BOOK":
            return '1 point per page'
        elif media_type == "MANGA":
            return '0.2 points per page'
        elif media_type == "VN":
            return '1/350 points/character'
        elif media_type == "ANIME":
            return '9.5 points per episode'
        elif media_type == "LISTENING":
            return '0.45 points/min of listening'
        elif media_type == "READTIME":
            return '0.45 points/min of reading time'
        elif media_type == "READING":
            return '1/350 points/character of reading'
        else:
            raise Exception(f'Unknown media type: {media_type}')
        
    def _to_points(media_type, amount):
        if media_type =="BOOK":
            return amount
        elif media_type =="MANGA":
            return amount * 0.2
        elif media_type =="VN":
            return amount / 350.0
        elif media_type =="ANIME":
            return amount * 9.5
        elif media_type =="LISTENING":
            return amount * 0.45
        elif media_type =="READTIME":
            return amount * 0.45
        elif media_type =="READING":
            return amount / 350.0
        else:
            raise Exception(f'Unknown media type: {media_type}')
        
    def filter_logs(logs, now, tf, media_type):
        if tf == "week":
            last_week = now - timedelta(days=8)
            tf_logs = [l for l in logs if l.created_at > last_week]
        elif tf == "month":
            tf_logs = [l for l in logs if l.created_at.month == now.month and l.created_at.year == now.year]
        elif tf == "all":
            tf_logs = logs
        else:
            raise Exception(f'Unknown timeframe {tf}')

        if not media_type:
            return tf_logs
        else:
            return [l for l in tf_logs if l.media_type == media_type]


class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tmw = self.bot.get_guild(617136488840429598)
    
    @app_commands.command(name="log", description="Log your immersion.")
    @app_commands.checks.has_role("Moderator")
    @app_commands.choices(media = [Choice(name="Book", value="BOOK"), Choice(name="Manga", value="MANGA"), Choice(name="Visual Novel", value="VN"), Choice(name="Anime", value="ANIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Readtime", value="READTIME")])
    async def log(self, interaction: discord.Interaction, media: str, amount: int, description: Optional[str] = None):
        if interaction.channel.id != 814947177608118273:
            return await interaction.response.send_message(ephemeral=True, content=f"""Can't log in here. Use <#814947177608118273> to log.""")
        
        Store.new_log(db_name, interaction.guild_id, interaction.user.id, media, amount, description, interaction.created_at)
        logs = Store.get_logs_by_user(db_name, interaction.guild_id, interaction.user.id)
        month_logs = Helpers.filter_logs(logs=logs, now=interaction.created_at, tf="month")
        old_points = sum(Helpers._to_points(l.media_type, l.amount) for l in month_logs)
        diff = Helpers._to_points(media_type=media, amount=amount)
        await interaction.response.send_message(content=f'{interaction.user.name} logged {amount} {Helpers._media_type_counter(media_type=media)} of {media.lower()} {emoji("InuPero")}\n{Helpers.media_type_converter_help(media_type=media)} → +{diff} points\n{interaction.created_at.strftime("%B")}: ~~{old_points}~~ → {old_points + diff}\n{description if description else ""}')
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))                    
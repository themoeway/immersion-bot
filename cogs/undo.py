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

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tmw = self.bot.get_guild(617136488840429598)
    
    @app_commands.command(name="undo", description="undo your log.")
    @app_commands.checks.has_role("Moderator")
    @app_commands.choices(media = [Choice(name="Book", value="BOOK"), Choice(name="Manga", value="MANGA"), Choice(name="Visual Novel", value="VN"), Choice(name="Anime", value="ANIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Readtime", value="READTIME")])
    async def undo(self, interaction: discord.Interaction, media: str, amount: int, message_link: str):
        return
#         await interaction.response.defer(ephemeral=True)
#         message_link = message_link.split('/')
#         channel = await self.bot.fetch_channel(message_link[5])
#         message = await channel.fetch_message(message_link[6])
#         delete_query = f'DELETE FROM logs WHERE discord_user_id={interaction.user.id} AND media_type={media} AND amount={amount} AND created_at={message.created_at + timedelta(hours=1).strftime("%y-%m-%d %H:%M:%S.%f")}'
        
        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))                   

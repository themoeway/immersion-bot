import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from sql import Store
import xlsxwriter
import os
import asyncio
import helpers

#############################################################

_DB_NAME = 'prod.db'

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guildid = data_dict["guild_id"]
    _COMMANDS_CHANNEL_ID = data_dict["_COMMANDS_CHANNEL_ID"]
    
MULTIPLIERS = {
    'BOOK': 1,
    'MANGA': 0.2,
    'VN': 1 / 350,
    'ANIME': 9.5,
    'READING': 1 / 350,
    'LISTENING': 0.45,
    'READTIME': 0.45
}
  
#############################################################

class Export(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)
                
    @app_commands.command(name='export', description=f'Export your immersion logs.')
    @app_commands.describe(timeframe='''Span of logs used.''')
    @app_commands.choices(timeframe = [Choice(name="Monthly", value="Monthly"), Choice(name="All Time", value="All Time"), Choice(name="Weekly", value="Weekly"), Choice(name="Yearly", value="Yearly")])
    @app_commands.choices(media_type = [Choice(name="Visual Novels", value="VN"), Choice(name="Manga", value="MANGA"), Choice(name="Anime", value="ANIME"), Choice(name="Book", value="BOOK"), Choice(name="Readtime", value="READTIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Reading", value="READING")])
    @app_commands.describe(date='''See past user overviews, combine it wit timeframes: [year-month-day] Example: '2022-12-29'.''')
    async def export(self, interaction: discord.Interaction, timeframe: str, media_type: Optional[str], date: Optional[str]):
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
    
        await interaction.response.defer()

        if not date:
            now = datetime.now()
        else:
            now = datetime.now().replace(year=int(date.split("-")[0]), month=int(date.split("-")[1]), day=int(date.split("-")[2]), hour=0, minute=0, second=0, microsecond=0)
        
        def _to_amount(media_type, points):
            if media_type == "BOOK":
                return points
            elif media_type == "MANGA":
                return points * 0.2
            elif media_type == "VN":
                return points / 350.0
            elif media_type == "ANIME":
                return points * 9.5
            elif media_type == "LISTENING":
                return points * 0.45
            elif media_type == "READTIME":
                return points * 0.45
            elif media_type == "READING":
                return points / 350.0
            else:
                raise Exception(f'Unknown media type: {media_type}')
        
        now, start, end, title = helpers.start_end_tf(now, timeframe)
        store = Store(_DB_NAME)
        logs = store.get_logs_by_user(429002040488755211, media_type, (now, start, end))
        workbook = xlsxwriter.Workbook(f'''{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx''')
        worksheet = workbook.add_worksheet('Logs')
        row_Index = 1
        for i, row in enumerate(logs):
            worksheet.write('A' + str(row_Index), row.media_type.value)
            worksheet.write('B' + str(row_Index), _to_amount(row.media_type.value, row.amount))
            worksheet.write('C' + str(row_Index), str(row.note))
            worksheet.write('D' + str(row_Index), str(row.created_at))
            row_Index += 1
        workbook.close()
        await interaction.delete_original_response()
        await interaction.channel.send(file=discord.File(fr'''{[file for file in os.listdir() if file == f"{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx"][0]}'''))
        
        await asyncio.sleep(1)

        for file in os.listdir():
            if file == f'''{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx''':
                os.remove(f'''{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx''')

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Export(bot))
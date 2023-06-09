import discord
from discord.ext import commands
from datetime import datetime
from datetime import date as new_date, datetime, timedelta
import json
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice

from collections import defaultdict
import math
import matplotlib.pyplot as plt
import pandas as pd

from enum import Enum
import sqlite3
from sql import Store
import os 

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

class SqliteEnum(Enum):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return self.name

class MediaType(SqliteEnum):
    BOOK = 'BOOK'
    MANGA = 'MANGA'
    READTIME = 'READTIME'
    READING = 'READING'
    VN = 'VN'
    ANIME = 'ANIME'
    LISTENING = 'LISTENING'

class User(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)
    
    async def start_end_tf(self, now, timeframe):
        if timeframe == "Weekly":
            start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            title = f"""{now.year}'s {timeframe} Leaderboard"""
            
        if timeframe == "Monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (now.replace(day=28) + timedelta(days=4)) - timedelta(days=(now.replace(day=28) + timedelta(days=4)).day)
            title = f"""Monthly ({now.strftime("%B")} {now.year}) Leaderboard"""
            
        if timeframe == "All Time":
            start = datetime(year=2020, month=3, day=4, hour=0, minute=0, second=0, microsecond=0)
            end = now
            title = f"""All time Leaderboard till {now.strftime("%B")} {now.year}"""
        
        if timeframe == "Yearly":
            start = now.date().replace(month=1, day=1)
            end = now.date().replace(month=12, day=31)
            title = f"{now.year}'s Leaderboard"

        return now, start, end, title
    
    async def generate_trend_graph(self, timeframe, interaction, weighed_points_mediums, logs):

        def daterange(start_date, end_date):
                for n in range(int((end_date - start_date).days)):
                    yield start_date + timedelta(n)
        
        def month_year_iter(start_month, start_year, end_month, end_year):
            ym_start= 12 * start_year + start_month - 1
            ym_end= 12 * end_year + end_month - 1
            for ym in range(ym_start, ym_end):
                y, m = divmod(ym, 12)
                yield y, m+1
        
        log_dict = defaultdict(lambda: defaultdict(lambda: 0))
        logs = list(reversed(logs))
        start_date, end_date = logs[0].created_at, logs[-1].created_at
        
        if timeframe == "All Time":
            for year, month in month_year_iter(start_date.month, start_date.year, end_date.month, end_date.year):
                for media_type in reversed(MediaType):
                    log_dict[media_type.value].setdefault((new_date(year, month, 1).strftime("%b/%y")), 0)
            for log in logs:
                log_dict[log.media_type.value][log.created_at.strftime("%b/%y")] += helpers._to_amount(log.media_type, log.amount)

        else:
            # Set empty days to 0
            for media_type in reversed(MediaType):
                for date in daterange(start_date, end_date):
                    log_dict[media_type.value].setdefault(date.date(), 0)
            for log in logs:
                log_dict[log.media_type.value][log.created_at.date()] += helpers._to_amount(log.media_type, log.amount)
            log_dict = dict(sorted(log_dict.items()))

        fig, ax = plt.subplots(figsize=(16, 12))
        plt.title(f'{timeframe} Immersion ', fontweight='bold', fontsize=50)
        plt.ylabel('Points', fontweight='bold', fontsize=30)
        
        # print({k: dict(v) for k, v in log_dict.items()})
        df = pd.DataFrame(log_dict)
        df = df.fillna(0)
        # print(df)
        
        color_dict = {
            "BOOK": "tab:orange",
            "MANGA": "tab:red",
            "READTIME": "tab:pink",
            "READING": "tab:green",
            "VN": "tab:cyan",
            "ANIME": "tab:purple",
            "LISTENING": "tab:blue",
        }

        accumulator = 0
        for media_type in df.columns:
            col = df[media_type]
            ax.bar(df.index, col,
                bottom=accumulator,
                color=color_dict[media_type])

            accumulator += col

        ax.legend(df.columns)

        plt.xticks(df.index, fontsize=20, rotation=45, horizontalalignment='right')
        fig.savefig(f"{interaction.user.id}_overview_chart.png")
        
    
    async def create_embed(self, timeframe, interaction, weighed_points_mediums, logs):
        embed = discord.Embed(title=f'{timeframe} Immersion Overview')
        embed.add_field(name='**User**', value=interaction.user.display_name)
        embed.add_field(name='**Timeframe**', value=timeframe)
        embed.add_field(name='**Points**', value=helpers.millify(sum(i for i, j in list(weighed_points_mediums.values()))))
        amounts_by_media_desc = '\n'.join(f'{key}: {helpers.millify(weighed_points_mediums[key][1])} {helpers.media_type_format(key)} → {helpers.millify(weighed_points_mediums[key][0])} pts' for key in weighed_points_mediums)
        embed.add_field(name='**Breakdown**', value=amounts_by_media_desc or 'None', inline=False)
        await self.generate_trend_graph(timeframe, interaction, weighed_points_mediums, logs)
        file = discord.File(fr'''{[file for file in os.listdir() if file.endswith('_overview_chart.png')][0]}''')
        embed.set_image(url=f"attachment://{interaction.user.id}_overview_chart.png")
        return embed, file
                
    @app_commands.command(name='user', description=f'Immersion overview of a user.')
    @app_commands.describe(timeframe='''Span of logs used.''')
    @app_commands.choices(timeframe = [Choice(name="Monthly", value="Monthly"), Choice(name="All Time", value="All Time"), Choice(name="Weekly", value="Weekly"), Choice(name="Yearly", value="Yearly")])
    @app_commands.choices(media_type = [Choice(name="Visual Novels", value="VN"), Choice(name="Manga", value="MANGA"), Choice(name="Anime", value="ANIME"), Choice(name="Book", value="BOOK"), Choice(name="Readtime", value="READTIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Reading", value="READING")])
    @app_commands.describe(date='''See past user overviews, combine it wit timeframes: [year-month-day] Example: '2022-12-29'.''')
    async def user(self, interaction: discord.Interaction, user: discord.User, timeframe: str, media_type: Optional[str], date: Optional[str]):        
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
    
        await interaction.response.defer()

        if not date:
            now = datetime.now()
        else:
            now = datetime.now().replace(year=int(date.split("-")[0]), month=int(date.split("-")[1]), day=int(date.split("-")[2]), hour=0, minute=0, second=0, microsecond=0)
        
        now, start, end, title = await self.start_end_tf(now, timeframe)
        store = Store(_DB_NAME)
        logs = store.get_logs_by_user(236887182571339777, media_type, (now, start, end))
        weighed_points_mediums = helpers.multiplied_points(logs)
        embed, file = await self.create_embed(timeframe, interaction, weighed_points_mediums, logs)
        
        await interaction.delete_original_response()
        await interaction.channel.send(embed=embed, file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(User(bot))
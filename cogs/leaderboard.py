import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import sys
from typing import Optional
from discord.app_commands import Choice
from db import Store
from common import emoji, get_member, millify, make_ordinal
from datetime import date as new_date, datetime, timedelta, strftime
from enum import Enum

db_name = "logs.db"

class Timeframe(Enum):
    @property
    def to_ly(self):
        if self == 'week':
            return 'weekly'
        if self == 'month':
            return 'monthly'
        if self == 'all':
            return 'all time'
        if isinstance(self, int):
            return f"""{self}'s"""
        else:
            raise f"Unknown Enum {self}"

class Helpers:
    def _to_amount(media_type, points):
        if media_type == "BOOK":
            return points
        elif media_type == "MANGA":
            return points * 5
        elif media_type == "VN":
            return points * 350.0
        elif media_type == "ANIME":
            return points / 9.5
        elif media_type == "LISTENING":
            return points / 0.45
        elif media_type == "READTIME":
            return points / 0.45
        elif media_type == "READING":
            return points * 350.0
        else:
            raise Exception(f'Unknown media type: {media_type}')


class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tmw = self.bot.get_guild(617136488840429598)
    
    #I want to allow the user to specify the timeframe for the leaderboard output, so from and until
    #But if somebody wants to see the all time or monthly leaderboard they would have to re enter all the dates again
    # so a shortcut parameter to quickly access monthly, all, weekly, yearly leaderboards
    #they should not overlap 
    @app_commands.command(name="leaderboard", description="See the immersion leaderboards.")
    @app_commands.checks.has_role("Moderator")
    @app_commands.choices(media = [Choice(name="Book", value="BOOK"), Choice(name="Manga", value="MANGA"), Choice(name="Visual Novel", value="VN"), Choice(name="Anime", value="ANIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Readtime", value="READTIME")])
    # @app_commands.choices(month = [Choice(name="January", value=1), Choice(name="February", value=2), Choice(name="March", value=3), Choice(name="April", value=4), Choice(name="Mai", value=5), Choice(name="June", value=6), Choice(name="July", value=7), Choice(name="August", value=8), Choice(name="September", value=9), Choice(name="October", value=10), Choice(name="November", value=11), Choice(name="December", value=12)])
    @app_commands.choices(week = [Choice(name="This week", value="week"), Choice(name="This month", value="month"), Choice(name="This year", value="year"), Choice(name="All", value="all")])
    async def leaderboard(self, interaction: discord.Interaction, shortcut: Optional[int] = "month", From: Optional[str] = None, until: Optional[str] = None, media: Optional[str] = None):
        await interaction.response.defer()
        if From and not until or until and not From:
            return await interaction.edit_original_response(content='Please specify both ends of the timeframe.')
        if From and until:
            From = From + " " + "00:00:00.000000"
            until = until + " " + "00:00:00.000000"
        if From and until and shortcut:
            shortcut == None
        if isinstance(shortcut, int):
            now = datetime.now().replace(year=shortcut)
            
        user_id = interaction.user.id
        leaderboard = Store.get_leaderboard(db_name, interaction.user.id (shortcut, From, until), media)
        user_rank = [rank for uid, total, rank in leaderboard if uid == user_id]
        user_rank = user_rank and user_rank[0]


        async def leaderboard_row(user_id, points, rank):
            ellipsis = '...\n' if user_rank and rank == (user_rank-1) and rank > 21 else ''
            user = await get_member(self.bot, interaction.guild, user_id)
            display_name = user.display_name if user else 'Unknown'
            amount = Helpers._to_amount(media, points) if media else points
            return f'{ellipsis}**{make_ordinal(rank)} {display_name}**: {millify(amount)}'

        leaderboard_desc = '\n'.join([await leaderboard_row(*row) for row in leaderboard])
        title_args = [
            shortcut.to_ly,
            media.value.lower() if media else '',
            'leaderboard',
            f'({Helpers._media_type_counter(media)})' if media else '(pts)'
        ]
        title = ' '.join(title_args).title()
        embed = discord.Embed(title=title, description=leaderboard_desc)
        
        await interaction.edit_original_response(embed=embed)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))                    
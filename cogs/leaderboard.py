import discord
from discord.ext import commands
from datetime import datetime
from datetime import timedelta
import json
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice

from sql import Store
import helpers

#############################################################

_DB_NAME = 'prod.db'

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guildid = data_dict["guild_id"]
  
#############################################################

class Leaderboard(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)
        
    @app_commands.command(name='leaderboard', description=f'Leaderboard of immersion.')
    @app_commands.describe(timeframe='''Span of logs used.''')
    @app_commands.choices(timeframe = [Choice(name="Monthly", value="Monthly"), Choice(name="All Time", value="All Time"), Choice(name="Weekly", value="Weekly"), Choice(name="Yearly", value="Yearly")])
    @app_commands.choices(media_type = [Choice(name="Visual Novels", value="VN"), Choice(name="Manga", value="MANGA"), Choice(name="Anime", value="ANIME"), Choice(name="Book", value="BOOK"), Choice(name="Readtime", value="READTIME"), Choice(name="Listening", value="LISTENING"), Choice(name="Reading", value="READING")])
    @app_commands.describe(date='''See past leaderboards, combine it wit timeframes: [year-month-day] Example: '2022-12-29'.''')
    async def leaderboard(self, interaction: discord.Interaction, timeframe: str, media_type: Optional[str], date: Optional[str]):
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
    
        await interaction.response.defer()
        
        if not date:
            now = datetime.now()
        else:
            now = datetime.now().replace(year=int(date.split("-")[0]), month=int(date.split("-")[1]), day=int(date.split("-")[2]), hour=0, minute=0, second=0, microsecond=0)
        
        now, start, end, title = helpers.start_end_tf(now, timeframe)
        store = Store(_DB_NAME)
        leaderboard = store.get_leaderboard(interaction.user.id, (now, start, end), media_type)
        user_rank = [rank for uid, total, rank in leaderboard if uid == interaction.user.id]
        user_rank = user_rank and user_rank[0]
        
        async def leaderboard_row(user_id, points, rank):
            ellipsis = '...\n' if user_rank and rank == (user_rank-1) and rank > 21 else ''
            try:
                user = await self.bot.fetch_user(user_id)
                display_name = user.display_name if user else 'Unknown'
                amount = helpers._to_amount(media_type, points) if media_type else points
            except Exception:
                display_name = 'Unknown'
            return f'{ellipsis}**{helpers.make_ordinal(rank)} {display_name}**: {helpers.millify(amount)}'

        leaderboard_desc = '\n'.join([await leaderboard_row(*row) for row in leaderboard])
        title = title + (" for " + media_type if media_type else "") + " (" + helpers.media_type_format(media_type) + ")" if media_type else ""
        embed = discord.Embed(title=title, description=leaderboard_desc)
        
        await interaction.edit_original_response(embed=embed)
   
        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))

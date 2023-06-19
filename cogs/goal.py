import discord
from discord.ext import commands
from datetime import datetime
from datetime import date as new_date, datetime, timedelta
from datetime import timedelta
import json
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice

from vndb_thigh_highs import VNDB
from vndb_thigh_highs.models import VN
import re
from AnilistPython import Anilist
from discord.ui import Select
from sql import Set_Goal, Store

import time

import helpers
import os
from dotenv import load_dotenv

#############################################################

load_dotenv()

_DB_NAME = 'prod.db'
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guildid = data_dict["guild_id"]
  
#############################################################

# class MyView(discord.ui.View):
#     def __init__(self, *, timeout: Optional[float] = 900, data, beginning_index: int, end_index: int):
#         super().__init__(timeout=timeout)
#         self.data: list = data
#         self.beginning_index: int = beginning_index
#         self.ending_index: int = end_index
    
    
#     async def edit_embed(self, data, beginning_index, ending_index):
#         myembed = discord.Embed(title=f'{len(data)} Goals found.')
#         for result in data[beginning_index:ending_index]:
#             myembed.add_field(name=f'{result[0]}: {result[1]}',value=f'{result[2]}', inline=False)
#         if len(data) >= 2:
#             myembed.set_footer(text="... not all results displayed but you can pick any index.\n" 
#                                     "Pick an index to retrieve a scene next.")
#         else:
#             myembed.set_footer(text="Pick an index to retrieve a scene next.")
#         return myembed
        
        
#     @discord.ui.button(label='≪', style=discord.ButtonStyle.grey, row=1)
#     async def go_to_first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.beginning_index -= 10
#         self.ending_index -= 10
#         if self.beginning_index >= len(self.data):
#             self.beginning_index = 0
#             self.ending_index = 10
#         myembed = await self.edit_embed(self.data, self.request, self.beginning_index, self.ending_index)
#         await interaction.response.edit_message(embed=myembed)
        
        
#     @discord.ui.button(label='Back', style=discord.ButtonStyle.blurple, row=1)
#     async def go_to_previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.beginning_index -= 5
#         self.ending_index -= 5
#         myembed = await self.edit_embed(self.data, self.request, self.beginning_index, self.ending_index)
#         await interaction.response.edit_message(embed=myembed)
    
    
#     @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple, row=1)
#     async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.beginning_index += 5
#         self.ending_index += 5
#         myembed = await self.edit_embed(self.data, self.request, self.beginning_index, self.ending_index)
#         await interaction.response.edit_message(embed=myembed)        
        
        
#     @discord.ui.button(label='≫', style=discord.ButtonStyle.grey, row=1)
#     async def go_to_last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.beginning_index += 10
#         self.ending_index += 10
#         if self.beginning_index >= len(self.data):
#             self.beginning_index -= 10
#             self.ending_index -= 10
#         myembed = await self.edit_embed(self.data, self.request, self.beginning_index, self.ending_index)
#         await interaction.response.edit_message(embed=myembed)
        
        
#     @discord.ui.button(label='Quit', style=discord.ButtonStyle.red, row=1)
#     async def stop_pages(self, interaction: discord.Interaction, button: discord.ui.Button):
#         await interaction.message.delete()

class Goal(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)
    
    async def point_message_converter(self, media_type, amount, name):
        if media_type == "Visual Novel":
            amount = amount / 350
            if name and name.startswith("v"):
                vndb = VNDB()
                vns = vndb.get_vn(VN.id == name[1:])
                vn = vns[0]
                return amount, "chars", f"1/350 points/characters → +{round(amount, 2)} points", ("on " + "[" + vn.title + "]" + "(" + f"<https://vndb.org/{name}>" + ")" if name else "")
            if name:
                return amount, "chars", f"1/350 points/characters → +{round(amount, 2)} points", name
            return amount, "chars", f"1/350 points/characters → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Manga":
            amount = amount * 0.2
            if name and name.isdigit():
                anilist = Anilist()
                updated_title = anilist.get_manga_with_id(name)["name_english"].replace(" ", "-")
                return amount, "pgs", f"0.2 points per page → +{round(amount, 2)} points", ("on " + "[" + anilist.get_manga_with_id(name)["name_english"] + "]" + "(" + f"<https://anilist.co/manga/{name}/{updated_title}/>" + ")" if name else "")
            if name:
                return amount, "pgs", f"0.2 points per page → +{round(amount, 2)} points", name
            return amount, "pgs", f"0.2 points per page → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Book":
            if name:
               return amount, "pgs", f"1 point per page → +{round(amount, 2)} points", ("on " + name if name else "")
            return amount, "pgs", f"1 point per page → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Anime":
            amount = amount * 9.5
            if name and name.isdigit():
                anilist = Anilist()
                updated_title = anilist.get_anime_with_id(name)["name_english"].replace(" ", "-")
                return amount, "eps", f"9.5 points per eps → +{round(amount, 2)} points", ("on " + "[" + anilist.get_anime_with_id(name)["name_english"] + "]" + "(" + f"<https://anilist.co/anime/{name}/{updated_title}/>" + ")" if name else "")
            if name:
                return amount, "eps", f"9.5 points per eps → +{round(amount, 2)} points", name
            return amount, "eps", f"9.5 points per eps → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Reading":
            amount = amount / 350
            if name:
                return amount, "pgs", f"1/135 points/character of reading → +{round(amount, 2)} points", name
            return amount, "pgs", f"1/135 points/character of reading → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Readtime":
            amount = amount * 0.45
            if name:
                return amount, "mins", f"0.45 points/min of listening → +{round(amount, 2)} points", name
            return amount, "mins", f"0.45 points/min of listening → +{round(amount, 2)} points", f"of {media_type}" 
        
        if media_type == "Listening":
            amount = amount * 0.45
            if name:
                return amount, "mins", f"0.45 points/min of listening → +{round(amount, 2)} points", name
            return amount, "mins", f"0.45 points/min of listening → +{round(amount, 2)} points", f"of {media_type}" 
    
    @app_commands.command(name='set_goal_media', description=f'Set daily immersion log goals')
    @app_commands.describe(amount='''Episode to watch, characters or pages to read. Time to read/listen in [hr:min] or [min] for example '1.30' or '25'.''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    @app_commands.describe(name='''You can use vndb IDs for VN and Anilist codes for Anime, Manga and Light Novels''')
    @app_commands.describe(span='''Set the span of your goal. [Day = Till the end of today], [Daily = Everyday], [Date = Till a certain date ([year-month-day] Example: '2022-12-29')]''')
    async def set_goal(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], span: Optional[str]):
        if interaction.channel.id != CHANNEL_ID:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
        
        store = Set_Goal("goals.db")
        goal_type = "MEDIA"
        bool = store.check_goal_exists(interaction.user.id, goal_type, media_type.upper(), (helpers.point_message_converter(media_type.upper(), int(amount), name if name else ""))[3])
        if bool:
            return await interaction.edit_original_response(content='You already set this goal.')    
        
        
        if media_type == "Listening" or media_type == "Readtime":
            if ":" in amount:
                hours, min = amount.split(":")
                amount = int(hours) * 60 + int(min)
            else:
                amount = int(amount)
        else:
            amount = int(amount)
            
        if not amount > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numers allowed.')
        
        if amount in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')
        
        if span.upper() == "DAY":
            span = "DAY"
            created_at = interaction.created_at
            end = interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif span.upper() == "DAILY":
            span = "DAILY"
            created_at = interaction.created_at
            end = interaction.created_at + timedelta(days=1)
        else:
            created_at = interaction.created_at
            try:
                end = interaction.created_at.replace(year=int((span.split("-"))[2]), month=int((span.split("-"))[1]), day=int((span.split("-"))[0]), hour=0, minute=0, second=0, microsecond=1)
            except Exception:
                return await interaction.response.send_message(ephemeral=True, content='Please enter the date in the correct format.')    
            else:
                span = "DATE"
                if end < created_at:
                    return await interaction.response.send_message(ephemeral=True, content='''You can't set goals for the past.''')
        
        store.new_goal(interaction.user.id, "MEDIA" ,media_type.upper(), amount, (helpers.point_message_converter(media_type.upper(), amount, name if name else ""))[3], span, created_at, end)

        await interaction.edit_original_response(content=f'''## Set {goal_type} goal as {span} goal\n- {amount} {helpers.media_type_format(media_type.upper())} {(helpers.point_message_converter(media_type.upper(), amount, name))[3]}\n\nUse ``/goals`` to view your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D>''')
      
    @app_commands.command(name='set_goal_points', description=f'Set daily immersion log goals')
    @app_commands.describe(amount='''Points to log.''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading"), Choice(name="Anything", value="Anything")])
   @app_commands.describe(span='''Set the span of your goal. [Day = Till the end of today], [Daily = Everyday], [Date = Till a certain date ([year-month-day] Example: '2022-12-29')]''')
    async def set_goal_points(self, interaction: discord.Interaction, media_type: str, amount: int, span: Optional[str]):
        if interaction.channel.id != CHANNEL_ID:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
            
        store = Set_Goal("goals.db")
        goal_type = "POINTS"
        bool = store.check_goal_exists(interaction.user.id, goal_type, media_type.upper(), f"of {media_type.upper()}")
        if bool:
            return await interaction.response.send_message(ephemeral=True, content='You already set this goal.')    
        
        if not amount > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numers allowed.')
        
        if amount in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')
        
        if span.upper() == "DAY":
            span = "DAY"
            created_at = interaction.created_at
            end = interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif span.upper() == "DAILY":
            span = "DAILY"
            created_at = interaction.created_at
            end = interaction.created_at + timedelta(days=1)
        else:
            created_at = interaction.created_at
            try:
                end = interaction.created_at.replace(year=int((span.split("-"))[2]), month=int((span.split("-"))[1]), day=int((span.split("-"))[0]), hour=0, minute=0, second=0, microsecond=0)
            except Exception:
                return await interaction.response.send_message(ephemeral=True, content='Please enter the date in the correct format.')    
            else:
                span = "DATE"
                if end < created_at:
                    return await interaction.response.send_message(ephemeral=True, content='''You can't set goals for the past.''')
        
        store.new_point_goal(interaction.user.id, "POINTS", media_type.upper(), amount, f"of {media_type.upper()}", span, created_at, end)
        await interaction.response.send_message(ephemeral=True, content=f'''## Set {goal_type} goal as {span} goal\n- {amount} {helpers.media_type_format(media_type.upper())} {" of " + media_type.upper()}\n\nUse ``/goals`` to view your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D>''')
        
    @app_commands.command(name='goals', description=f'See your immersion log goal overview.')
    async def goals(self, interaction: discord.Interaction):
        if interaction.channel.id != CHANNEL_ID:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')

        store = Set_Goal("goals.db")
        goals = store.get_goals(interaction.user.id)
        
        if not goals:
            return await interaction.response.send_message(ephemeral=True, content='No goals found. Set goals with ``/set_goal``.')
        
        goals_description = []
        
        store = Store("prod.db")
        beginn = goals[0].created_at
        end = interaction.created_at #or goals[-1].created_at
        
        relevant_logs = store.get_goal_relevant_logs(interaction.user.id, beginn, end)
        
        if not relevant_logs:
            for goal_row in goals:
                goals_description.append(f"""- 0/{goal_row.amount} {helpers.media_type_format(goal_row.media_type.value) if goal_row.goal_type == "MEDIA" else "points"} {goal_row.text} ({goal_row.span}{"=" + str(goal_row.end) if goal_row.span == "DATE" else ""})""")
            goals_description = '\n'.join(goals_description)
            
            return await interaction.response.send_message(ephemeral=True, content=f'''## {interaction.user.display_name}'s Goal Overview\n{goals_description if goals_description else "No goals found."}\n\nUse ``/set_goal`` to set your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D> and more!''')
    
        def first_occ(lst, item):
            return [i for i, x in enumerate(lst) if x.span == item]
    
        span_goals = [span for duid, gt, mt, amount, text, span, created_at, end in goals]
        if "DAY" or "DAILY" in goals:
            day_releveant_logs = [log for log in relevant_logs if interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) < log.created_at.replace(tzinfo=pytz.UTC) < (interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))] #will take logs from the day before the goals was created
        
        if "DATE" in span_goals:
            i =  first_occ(goals, "DATE")
            if i != []:
                date_relevant_logs = [log for log in relevant_logs if datetime.strptime(goals[0].created_at, "%Y-%m-%d %H:%M:%S.%f%z") < log.created_at.replace(tzinfo=pytz.UTC) < datetime.strptime(goals[-1].end, "%Y-%m-%d %H:%M:%S.%f%z")]
        
        for goals_row in goals:
            if goals_row.span == "DAY" or goals_row.span == "DAILY":
                points = []
                for log in day_releveant_logs:
                    if goals_row.text == (log.note.strip('][').split(', '))[0].replace("'", ""):
                        if goals_row.goal_type == "MEDIA":
                            points.append(log.pt)
                        if goals_row.goal_type == "POINTS":
                            points.append(helpers._to_amount(log.media_type.value, log.pt))
                        continue
                    if goals_row.media_type == log.media_type:
                        if goals_row.goal_type == "MEDIA":
                            points.append(log.pt)
                        if goals_row.goal_type == "POINTS":
                            points.append(helpers._to_amount(log.media_type.value, log.pt))
                        continue
                points = sum(points)
                if points >= goals_row.amount:
                    goals_description.append(f"""- ~~{points}/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} ({goals_row.span})~~""")
                else:
                    goals_description.append(f"""- {points}/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} ({goals_row.span})""")
                continue
            
            if goals_row.span == "DATE":  
                points = []
                for log in date_relevant_logs:
                    if goals_row.text == (log.note.strip('][').split(', '))[0].replace("'", ""):
                        if goals_row.goal_type == "MEDIA":
                            points.append(log.pt)
                        if goals_row.goal_type == "POINTS":
                            points.append(helpers._to_amount(log.media_type.value, log.pt))
                        continue
                    if goals_row.media_type == log.media_type:
                        if goals_row.goal_type == "MEDIA":
                            points.append(log.pt)
                        if goals_row.goal_type == "POINTS":
                            points.append(helpers._to_amount(log.media_type.value, log.pt))
                        continue
                points = sum(points)
                if points >= goals_row.amount:
                    goals_description.append(f"""- ~~{points}/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} ({goals_row.span})~~""")
                else:
                    goals_description.append(f"""- {points}/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} ({goals_row.span})""")
                continue
        goals_description = '\n'.join(goals_description)
  
            
        await interaction.response.send_message(ephemeral=True, content=f'''## {interaction.user.display_name}'s Goal Overview\n{goals_description if goals_description else "No goals found."}\n\nUse ``/set_goal`` to set your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D> and more!''')
        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Goal(bot))

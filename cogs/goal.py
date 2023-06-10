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

#############################################################

_DB_NAME = 'prod.db'

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
    @app_commands.choices(frequency = [Choice(name="Daily", value="Daily")])
    @app_commands.describe(frequency='Make this your daily goal for the month.')
    async def set_goal(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], frequency: Optional[str]):
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
        
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
        
        # async def goals_row(discord_user_id, media_type, amount, text, created_at):
        #     return f'''- {amount} {helpers.media_type_format(media_type.value)} {(helpers.point_message_converter(media_type.value, amount, name))[3]}'''
        store = Set_Goal("goals.db")
        bool = store.check_goal_exists(interaction.user.id, media_type.upper(), amount, f"of {media_type.upper()}", datetime.now(), frequency, 'goals')
        if bool:
            return await interaction.response.send_message(ephemeral=True, content='You already set this goal.')
        
        store.new_goal(interaction.user.id, media_type.upper(), amount, (helpers.point_message_converter(media_type.upper(), amount, name))[3], interaction.created_at, frequency)
        # goals = store.get_goals(interaction.user.id)
        # goals_description = '\n'.join([await goals_row(*row) for row in goals])
        # await interaction.edit_original_response(content=f'''## {interaction.user.display_name}'s Goal Overview\n{goals_description}\n\nTime till <t:{unixstamp}>''')
        await interaction.response.send_message(ephemeral=True, content=f'''## Set goal till <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timetuple()))}:R>:\n- {amount} {helpers.media_type_format(media_type.upper())} {(helpers.point_message_converter(media_type.upper(), amount, name))[3]}\n\nUse ``/goals`` to view your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D>''')
        
    @app_commands.command(name='set_goal_points', description=f'Set daily immersion log goals')
    @app_commands.describe(amount='''Points to log.''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading"), Choice(name="Anything", value="Anything")])
    @app_commands.choices(frequency = [Choice(name="Daily", value="Daily")])
    @app_commands.describe(frequency='Make this your daily goal for the month.')
    async def set_goal_points(self, interaction: discord.Interaction, media_type: str, amount: int, frequency: Optional[str]):
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
            
        if not amount > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numers allowed.')
        
        if amount in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')
        
        store = Set_Goal("goals.db")
        bool = store.check_goal_exists(interaction.user.id, media_type.upper(), amount, f"of {media_type.upper()}", datetime.now(), frequency, 'points')
        if bool:
            return await interaction.response.send_message(ephemeral=True, content='You already set this goal.')
        
        store.new_point_goal(interaction.user.id, media_type.upper(), amount, f"of {media_type.upper()}", datetime.now(), frequency)
        await interaction.response.send_message(ephemeral=True, content=f'''## Set goal till <t:{int(time.mktime((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timetuple()))}:R>:\n- {amount} points of {media_type}\n\nUse ``/goals`` to view your goals for <t:{int(time.mktime((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D>''')    
    
        
    @app_commands.command(name='goals', description=f'See your immersion log goal overview.')
    async def goals(self, interaction: discord.Interaction):
        if interaction.channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')

        async def goals_row(discord_user_id, media_type, amount, text, created_at, frequency):
            return f'''- {amount} {helpers.media_type_format(media_type.value)} {text}'''

        day_start = interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()
        
        timeframe = (day_start, now)
        store = Set_Goal("goals.db")
        goals = store.get_goals(interaction.user.id, timeframe)
        print(goals)
        goals = goals + store.get_daily_goals(interaction.user.id)
        print(goals)
        point_goals = store.get_point_goals(interaction.user.id, timeframe)
        
        print(point_goals)
        store = Store(_DB_NAME)
        recent_logs = store.get_recent_goal_alike_logs(interaction.user.id, (day_start, now))
        print(recent_logs)
        goals_description = []
        rl_notes_l = [note for media_type, amount, note in recent_logs]
        rl_media_type_l = [media_type for media_type, amount, note in recent_logs]
        rl_media_type_amount_l = [(media_type, amount) for media_type, amount, note in recent_logs]
        if goals:
            for goals_row in goals:
                if recent_logs:
                    if any(goals_row.text in text for text in rl_notes_l):
                        indices = helpers.indices_text(recent_logs, goals_row.text)
                        print(indices)
                        points = []
                        for i in indices:
                            points.append(recent_logs[i].da)
                        print(sum(points))
                        goals_description.append(f'''- {"~~" + str(int(sum(points))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text + "~~" if sum(points) >= goals_row.amount else str(int(sum(points))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                        continue
                        # for log in recent_logs:
                        #     log_note = log.note.strip('][').split(', ')
                        #     print(goals_row.text)
                        #     print(log_note[0].replace("'", ""))
                        #     if goals_row.text == log_note[0].replace("'", ""):
                        #         goals_description.append(f'''- {"~~" + str(int(log.da)) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text + "~~" if log.da >= goals_row.amount else str(int(log.da)) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                        #         continue
                        #     else:
                        #         continue
                    else:
                        goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                        break
                else:
                    goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                    continue
        
        if point_goals:
            for points_row in point_goals:
                if recent_logs:
                    if points_row.media_type in rl_media_type_l:
                        indices = helpers.indices_media(recent_logs, points_row.media_type)
                        points = []
                        for i in indices:
                            points.append(helpers._to_amount(recent_logs[i].media_type.value, recent_logs[i].da))
                        goals_description.append(f'''- {"~~" + str(sum(points)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "") + "~~" if sum(points) >= points_row.amount else str(sum(points)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "")}''')
                        continue
                    else:
                        print(points_row.media_type.value)
                        if points_row.media_type.value == "ANYTHING":
                            points = []
                            for media, amount in rl_media_type_amount_l:
                                points.append(helpers._to_amount(media.value, amount))
                            print(points)
                            goals_description.append(f'''- {"~~" + str(round(sum(points), 0)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "") + "~~" if sum(points) >= points_row.amount else str(round(sum(points), 0)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "")}''')
                            continue
                        else:
                            goals_description.append(f'''- {"~~" + "0" + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "") + "~~" if sum(points) >= points_row.amount else "0" + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "")}''')
                            break
                else:
                    goals_description.append(f'''- 0/{str(points_row.amount)} points {points_row.text} {(" (" + points_row.freq + ") " if points_row.freq != None else "")} ''')
                    continue
        goals_description = '\n'.join(goals_description)
        # if goals:
        #     for goals_row in goals:
        #         if recent_logs:
        #             for log in recent_logs:
        #                 log_note = log.note.strip('][').split(', ')
        #                 if any(goals_row.text in text for text in rl_notes_l):
        #                     if log_note[0].replace("'", "") == goals_row.text:
        #                         goals_description.append(f'''- {"~~" + str(int(log.da)) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text + "~~" if log.da >= goals_row.amount else str(int(log.da)) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text}''')
        #                         continue
        #                 if goals_row.media_type in rl_media_type_l:
        #                     goals_description.append(f'''- {"~~" + str(int(helpers._to_amount(log.media_type.value, log.da))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text + "~~" if helpers._to_amount(log.media_type.value, log.da) >= goals_row.amount else str(int(helpers._to_amount(log.media_type.value, log.da))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text}''')
        #                     continue
        #                 else:
        #                     goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text}''')
        #                     break
        #         else:
        #             goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text}''')
        #             continue
        #     goals_description = '\n'.join(goals_description)
            
        await interaction.response.send_message(ephemeral=True, content=f'''## {interaction.user.display_name}'s Goal Overview{(" till <t:" + str(int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timetuple()))) + ":R>:" if goals or point_goals else "")}\n{goals_description if goals_description else "No goals for today found."}\n\nUse ``/set_goal`` to set your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D> and more!''')
    
    # async def edit_results_post(self, results, results_msg, beginning_index, end_index, expression):
    #     myembed = discord.Embed(title=f"{len(results)} results for {expression}")
    #     for result in results[beginning_index:end_index]:
    #         myembed.add_field(name=f'{result[0]}: {result[1]}',value=f'{result[2]}', inline=False)
    #     if len(results) >= 5:
    #         myembed.set_footer(text="... not all results displayed but you can pick any index.\n"
    #                                 "Pick an index to retrieve a scene next.")
    #     else:
    #         myembed.set_footer(text="Pick an index to retrieve a scene next.")

    #     await results_msg.edit(embed=myembed)    
        
    # @app_commands.command(name='change_goals', description=f'Change your immersion goals.')
    # async def change_goals(self, interaction: discord.Interaction):
    #     if interaction.channel.id != 947813835715256393:
    #         return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')

    #     day_start = interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
    #     now = datetime.now()
        
    #     timeframe = (day_start, now)
    #     store = Set_Goal("goals.db")
    #     goals, g_table = store.get_goals(interaction.user.id, timeframe)
    #     goals = goals + store.get_daily_goals(interaction.user.id)
    #     point_goals, p_table = store.get_point_goals(interaction.user.id, timeframe)
        
    #     if len(goals + point_goals) == 0:
    #         await interaction.channel.send("No results.")
    #         return
        
    #     results = [list(tup)+[g_table[0]] for tup in goals] + [list(tup)+[p_table[0]] for tup in point_goals]
    #     myembed = discord.Embed(title=f'{len(results)} Goals found.')
    #     for result in results[0:5]:
    #         print(result)
    #         myembed.add_field(name=f'{result[3]}',value='a', inline=False)
    #     if len(results) >= 5:
    #         myembed.set_footer(text="... not all results displayed but you can pick any index.\n"
    #                            "Pick an index to retrieve a scene next.")
    #     else:
    #         myembed.set_footer(text="Pick an index to retrieve a scene next.")
    #     beginning_index = 0
    #     end_index = 5
        
    #     options = []
    #     for result in results[0:5]:
    #         item = discord.SelectOption(label=f'{result[3][:2]}')
    #         options.append(item)
            
    #     select = Select(min_values = 1, max_values = 1, options=options)   
    #     async def my_callback(interaction):
    #         relevant_result = select.view.data[(int(select.values[0])-1) + int(select.view.beginning_index)]      
    #         print(relevant_result)

    #     select.callback = my_callback
    #     view = MyView(data=results, beginning_index=beginning_index, end_index=end_index)
        
    #     #view.add_item(select)
    #     await interaction.channel.send(embed=myembed)
        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Goal(bot))

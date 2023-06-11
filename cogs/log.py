import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from typing import List
import json
from sql import Store, Set_Goal
import helpers
import logging
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
#############################################################

load_dotenv()

_DB_NAME = 'prod.db'
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guildid = data_dict["guild_id"]

log = logging.getLogger(__name__)
  
#############################################################


class Log(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)

    @app_commands.command(name='log', description=f'Log your immersion')
    @app_commands.describe(amount='''Episodes watched, characters or pages read. Time read/listened in [hr:min] or [min] for example '1.30' or '25'.''')
    @app_commands.describe(comment='''Comment''')
    @app_commands.describe(backlog='''Backlog to this date: [year-month-day] Example: December 1st 2022 '2022-12-01' ''')
    @app_commands.describe(name='''You can use vndb IDs and titles for VN and Anilist codes for Anime, Manga and Light Novels''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    async def log(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], comment: Optional[str], backlog: Optional[str]):
        await interaction.response.defer()
        if interaction.channel.id != CHANNEL_ID: 
        #if interaction.channel.id !=947813835715256393 or not isinstance(ctx.channel, discord.channel.DMChannel):
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
        
        #Handeling amount when its given as a time
        if media_type == "Listening" or media_type == "Readtime":
            if ":" in amount:
                hours, min = amount.split(":")
                amount = int(hours) * 60 + int(min)
            else:
                amount = int(amount)
        else:
            amount = int(amount)
            
        if not amount > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numbers allowed.')
        
        if amount in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')
        
        if backlog:
            now = datetime.now()
            created_at = datetime.now().replace(year=int(backlog.split("-")[0]), month=int(backlog.split("-")[1]), day=int(backlog.split("-")[2]), hour=0, minute=0, second=0, microsecond=0)
            if now < created_at:
                return await interaction.response.send_message(ephemeral=True, content='''You can't backlog in the future.''')
            if now > created_at:
                date = created_at
        if not backlog:
            date = datetime.now()
  
        def check_achievements(discord_user_id, media_type):
            logs = store.get_logs_by_user(discord_user_id, media_type, None)
            weighed_points_mediums = helpers.multiplied_points(logs)
            abmt = helpers.calc_achievements(weighed_points_mediums)
            if not bool(abmt):
                return 0, 0, 0, "", "", "", ""
            lower_interval, current_points, upper_interval, rank_emoji, rank_name, next_rank_emoji, next_rank_name = helpers.get_achievemnt_index(abmt)
            
            return lower_interval, current_points, upper_interval, rank_emoji, rank_name, next_rank_emoji, next_rank_name
        
        store = Set_Goal("goals.db")
        then = date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        now = interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
        
        goals = store.get_goals(interaction.user.id, (now, date)) + store.get_daily_goals(interaction.user.id) #getting goals for the current day and daily goals
        point_goals = store.get_point_goals(interaction.user.id, (now, date))# getting point goals
        
        store = Store("prod.db")
        first_date = date.replace(day=1, hour=0, minute=0, second=0) 
        calc_amount, format, msg, title = helpers.point_message_converter(media_type.upper(), amount, name)
        #returns weighed amount (i.e 1ep = 9.5 so weighed amount of 1 ANIME EP is 9.5), format (i.e chars, pages, etc), msg i.e 1/350 points/characters = x points, title is the anime/vn/manga title through anilist or vndb query
        old_points = store.get_logs_by_user(interaction.user.id, None, (first_date, date)) #query to get logs of past month for monlthy point overview i.e ~~June: 2k~~ -> June: 2.1k
        
        old_weighed_points_mediums = helpers.multiplied_points(old_points) 
        old_rank_achievement, old_achievemnt_points, old_next_achievement, old_emoji, old_rank_name, old_next_rank_emoji, old_next_rank_name = check_achievements(interaction.user.id, media_type.upper())
        #returns achievemnt progress before log is getting registered to compare with achievement progress after log
        
        store.new_log(interaction.guild_id, interaction.user.id, media_type.upper(), amount, [title, comment], date) #log being registered 
        
        current_rank_achievement, current_achievemnt_points, new_rank_achievement, new_emoji, new_rank_name, new_next_rank_emoji, new_next_rank_name = check_achievements(interaction.user.id, media_type.upper())
        #getting new achievement progress
     
        current_points = store.get_logs_by_user(interaction.user.id, None, (first_date, date)) #current total points
        current_weighed_points_mediums = helpers.multiplied_points(current_points)

        recent_logs = store.get_recent_goal_alike_logs(interaction.user.id, (now, date)) #getting logs of past day for goals

        async def goals_row(discord_user_id, req_media_type, req_amount, text, created_at, frequency):
            for log in recent_logs:
                if log.media_type.value == req_media_type:
                    if title == text:
                        return f'''- {"~~" + str(log.amount) + "/" + str(req_amount) + " " + str(helpers.media_type_format(req_media_type.value)) + " " + text + "~~" if log.amount >= req_amount else str(log.amount) + "/" + req_amount + str(helpers.media_type_format(req_media_type.value)) + text}'''
                    if title != text:
                        return 
                
        goals_description = []

        rl_notes_l = [note for media_type, amount, note in recent_logs]
        rl_media_type_l = [media_type for media_type, amount, note in recent_logs]
        rl_media_type_amount_l = [(media_type, amount) for media_type, amount, note in recent_logs]
        #handling goals, i.e watch 3 eps of anime, read 3000 chars of VN by comparing two lists (goals and recent_logs)
        if goals:
            for goals_row in goals:
                if recent_logs:
                    if any(goals_row.text in text for text in rl_notes_l):
                        indices = helpers.indices_text(recent_logs, goals_row.text)
                        points = []
                        for i in indices:
                            points.append(recent_logs[i].da)
                        goals_description.append(f'''- {"~~" + str(int(sum(points))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text + "~~" if sum(points) >= goals_row.amount else str(int(sum(points))) + "/" + str(int(goals_row.amount)) + " " + str(helpers.media_type_format(goals_row.media_type.value)) + " " + goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                        continue
                    else:
                        goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                        break
                else:
                    goals_description.append(f'''- 0/{goals_row.amount} {helpers.media_type_format(goals_row.media_type.value)} {goals_row.text} {"(" + goals_row.freq + ")" if goals_row.freq != None else ""}''')
                    continue
        
        #handling point_goals
        if point_goals:
            for points_row in point_goals:
                if recent_logs:
                    if points_row.media_type in rl_media_type_l:
                        indices = helpers.indices_media(recent_logs, points_row.media_type)
                        points = []
                        for i in indices:
                            points.append(helpers._to_amount(recent_logs[i].media_type.value, recent_logs[i].da))
                        goals_description.append(f'''- {sum(points)}/{points_row.amount} points {points_row.text} {"(" + points_row.freq + ")" if points_row.freq != None else ""}''')
                        continue
                    else:
                        if points_row.media_type.value == "ANYTHING":
                            points = []
                            for media, amount in rl_media_type_amount_l:
                                points.append(helpers._to_amount(media.value, amount))
                            goals_description.append(f'''- {"~~" + str(round(sum(points), 0)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "") + "~~" if sum(points) >= points_row.amount else str(round(sum(points), 0)) + "/" + str(points_row.amount) + " points " + points_row.text + (" (" + points_row.freq + ") " if points_row.freq != None else "")}''')
                            continue
                        else:
                            goals_description.append(f'''- 0/{points_row.amount} points {points_row.text} {"(" + points_row.freq + ")" if points_row.freq != None else ""}''')
                            break
                else:
                    goals_description.append(f'''- 0/{points_row.amount} points {points_row.text} {"(" + points_row.freq + ")" if points_row.freq != None else ""}''')
                    continue
        goals_description = '\n'.join(goals_description)

        print(goals_description)
    
        #final log message
        await interaction.edit_original_response(content=f'''{interaction.user.mention} logged {round(amount,2)} {format} {title}\n{msg}\n\n{"""__**Goal progression:**__
""" + str(goals_description) + """
""" if goals_description else ""}{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}\n{"""
**Next Achievement: **""" + new_next_rank_name + " " + new_next_rank_emoji + " in " + str(new_rank_achievement-current_achievemnt_points) + " " + helpers.media_type_format(media_type.upper()) if old_next_achievement == new_rank_achievement else """
**New Achievemnt Unlocked: **""" + new_rank_name + " " + new_emoji + " " + str(int(current_rank_achievement)) + " " + helpers.media_type_format(media_type.upper()) + """
**Next Achievement:** """ + new_next_rank_name + " " + new_next_rank_emoji + " " + str(int(new_rank_achievement)) + " " + helpers.media_type_format(media_type.upper())}\n\n{">>> " + comment if comment else ""}''')

    @log.autocomplete('name')
    async def log_autocomplete(self, interaction: discord.Interaction, current: str,) -> List[app_commands.Choice[str]]:

        await interaction.response.defer()
        suggestions = []

        if interaction.namespace['media_type'] == 'VN':
            url = 'https://api.vndb.org/kana/vn'
            data = {'filters': ['search', '=', f'{current}'], 'fields': 'title, alttitle'} # default no. of results is 10
        
        elif interaction.namespace['media_type'] == 'Anime':
            url = 'https://graphql.anilist.co'
            query = '''
            query ($page: Int, $perPage: Int, $title: String) {
                Page(page: $page, perPage: $perPage) {
                    pageInfo {
                        total
                        perPage
                    }
                    media (search: $title, type: ANIME) {
                        id
                        title {
                            romaji
                            native
                        }
                    }
                }
            }
            '''

            variables = {
                'title': current,
                'page': 1,
                'perPage': 10
            }

            data = {'query': query, 'variables': variables}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                log.info(resp.status)
                json_data = await resp.json()

                if interaction.namespace['media_type'] == 'VN':
                    suggestions = [(result['title'], result['id']) for result in json_data['results']]

                elif interaction.namespace['media_type'] == 'Anime':
                    suggestions = [(f"{result['title']['romaji']} ({result['title']['native']})", result['id']) for result in json_data['data']['Page']['media']]

                await asyncio.sleep(0)

                return [
                    app_commands.Choice(name=title, value=str(id))
                    for title, id in suggestions if current.lower() in title.lower()
                ]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))

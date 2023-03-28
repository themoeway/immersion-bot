import common
from common import MediaType, make_ordinal
from db import init_tables, Store
from discord.ext import commands
import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date as new_date, datetime, timedelta
from enum import Enum
from collections import defaultdict
from textwrap import dedent
import itertools
import logging
import discord
import tempfile
import pprint
from typing import Optional
from discord.utils import get
import time
from collections import namedtuple

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()
intents.message_content = True

help_command = commands.DefaultHelpCommand(no_category='Commands')
bot = commands.Bot(command_prefix='.', case_insensitive=True, help_command=help_command, intents=intents)

_ADMIN_ID = 297606972092710913
_COMMANDS_CHANNEL_ID = 814947177608118273
_GUILD_ID = 617136488840429598
_ADMIN_ROLE_IDS = None
_DB_NAME = 'main.db'
store = None

# BANNED_USERS = [35718317378191360, 242512550632095744, 319175553162936333]
BANNED_USERS = []

class Timeframe(Enum):
    WEEK = 'week'
    MONTH = 'month'
    ALL = 'all'

    @property
    def to_ly(self):
        if self == Timeframe.WEEK:
            return 'weekly'
        elif self == Timeframe.MONTH:
            return 'monthly'
        elif self == Timeframe.ALL:
            return 'all time'
        else:
            raise f"Unknown Enum {self}"


def _media_type_counter(media_type: MediaType):
    if media_type == MediaType.BOOK:
        return 'pgs'
    elif media_type == MediaType.MANGA:
        return 'pgs'
    elif media_type == MediaType.VN:
        return 'chars'
    elif media_type == MediaType.ANIME:
        return 'eps'
    elif media_type == MediaType.LISTENING:
        return 'mins'
    elif media_type == MediaType.READTIME:
        return 'mins'
    elif media_type == MediaType.READING:
        return 'chars'
    else:
        raise Exception(f'Unknown media type: {media_type}')


ACHIEVEMENTS = {
    MediaType.VN: [0, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000, 10_000_000, float('inf')],
    MediaType.ANIME: [0, 12, 25, 100, 200, 500, 800, 1500, float('inf')],
    # Reading combined here
    MediaType.BOOK: [0, 100, 250, 1000, 2500, 5000, 10_000, 20_000, float('inf')],
    MediaType.MANGA: [0, 250, 1250, 5000, 10_000, 25_000, 50_000, 100_000, float('inf')],
    MediaType.LISTENING: [0, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float('inf')],
    MediaType.READTIME: [0, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float('inf')],
}

PT_ACHIEVEMENTS = [0, 100, 300, 1000, 2000, 10_000, 25_000, 100_000, float('inf')]

ACHIEVEMENT_RANKS = ['Beginner', 'Initiate', 'Apprentice', 'Hobbyist', 'Enthusiast', 'Aficionado', 'Sage', 'Master']
ACHIEVEMENT_EMOJIS = [':new_moon:', ':new_moon_with_face:', ':waning_crescent_moon:', ':last_quarter_moon:', ':waning_gibbous_moon:', ':full_moon:', ':full_moon_with_face:', ':sun_with_face:']


def _set_globals():
    environment = os.environ.get('ENV')
    is_prod = environment == 'prod'
    global _ADMIN_ROLE_IDS
    global _DB_NAME
    if is_prod:
        print("Running on prod")
        _ADMIN_ROLE_IDS = [
            627149592579801128,  # Moderator role
        ]
        _DB_NAME = 'prod.db'
        


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    _set_globals()
    print(f'Initing tables on {_DB_NAME}')
    global store
    store = Store(_DB_NAME)
    init_tables(_DB_NAME)
    print('Done initing tables')

@bot.command(name='backfill', rest_is_raw=True)
async def on_message(ctx, log_date: str, media_type: str, amount: float, *, args: Optional[str]):
    created_at = datetime.strptime(log_date, '%Y-%m-%d')
    if created_at < datetime.now() - timedelta(days=90):
        await ctx.send('Not allowed to backfill anything before 90 days')
        return
    if created_at > datetime.now():
        await ctx.send('Not allowed to backfill in the future')
        return
    return await _log(ctx, created_at, media_type, amount, args)


LOG_HELP_TEXT = f"""
Log a record of your immersion
* Book [BOOK]: 1 point per page
* Manga [MANGA]: 0.2 points per page
* Visual Novel [VN]: 1/350 points/character
* Anime [ANIME]: 9.5 points per episode
* Reading [READING]: 1/350 points/character of reading
* Reading Time [READTIME]: 0.45 points/min of active reading
* Listening [LISTENING]: 0.45 points/min of active listening

Examples:
.log vn 20000 Chaos;Head Noah
.log listening 20 https://www.youtube.com/watch?v=LjbBa6DIFd8

"""



@bot.command(name='log', rest_is_raw=True, help=LOG_HELP_TEXT)
async def on_message(ctx, media_type: str, amount: float, *, args: Optional[str]):
    created_at = datetime.now()
    return await _log(ctx, created_at, media_type, amount, args)


async def _log(ctx, created_at: datetime, media_type: str, amount: float, args: Optional[str]):
    start_time = time.time()
    if not (isinstance(ctx.channel, discord.channel.DMChannel) or ctx.channel.id == _COMMANDS_CHANNEL_ID):
        await ctx.message.delete()
        return

    if isinstance(ctx.channel, discord.channel.DMChannel):
        channel = ctx.channel
    else:
        channel = bot.get_channel(_COMMANDS_CHANNEL_ID)
    try:
        media_type = MediaType[media_type.upper()]
    except KeyError:
        await channel.send(f'Unknown type {media_type}.')
        return

    if not amount > 0:
        await channel.send('Only positive numbers allowed')
        return

    if amount in [float('inf'), float('-inf')]:
        await channel.send('No infinities allowed')
        return

    if ctx.guild:
        guild_id = ctx.guild.id
    else:
        guild_id = _GUILD_ID

    user_id = ctx.author.id

    # I don't know why it adds an extra space with `rest_is_raw` passed in
    note = args[1:]
    logs = store.get_logs_by_user(guild_id, user_id)
    month_logs = filter_logs(logs, Timeframe.MONTH)
    old_points = sum_log_points(month_logs)
    
    store.new_log(guild_id, user_id, media_type, amount, note, created_at)
    diff = _to_points(media_type, amount)

    user = await common.get_member(bot, ctx.guild, user_id)
    await channel.send(
        f'**{user.display_name}** logged {amount:,g} {_media_type_counter(media_type)} of {media_type.value.lower()} {common.emoji("InuPero")}\n'
        f'{media_type_converter_help(media_type)} → +{diff:,g} points\n'
        f'{created_at.strftime("%B")}: ~~{old_points:,g}~~ → {old_points + diff:,g}'
    )
    if ctx.channel.id != _COMMANDS_CHANNEL_ID:
        await ctx.message.add_reaction(bot.get_emoji(837211306293067797))

    print(f'.log took {time.time() - start_time:g} secs.')


@bot.command(name='undo', help="undo your latest logs")
async def on_message(ctx, times: int = 1):
    if not (0 < times <= 10):
        await ctx.send('Please enter a number between 1 and 10.')
        return
    if not ctx.guild:
        guild_id = _GUILD_ID
    else:
        guild_id = ctx.guild.id
    user_id = ctx.author.id
    for i in range(times):
        logs = store.get_logs_by_user(guild_id, user_id)
        if not logs:
            await ctx.send(f'No more logs. Deleted {i} logs.')
            return
        store.delete_latest(guild_id, user_id)
    await ctx.send(f'Deleted the last {times} logs.')


ME_HELP_TEXT = """
Displays my overview by timeframe (default:month) [week|month|all]

Examples:
.me
.me week
.me all
"""


@bot.command(name='me', help=ME_HELP_TEXT)
async def on_message(ctx, timeframe: str = None):
    # if not isinstance(ctx.channel, discord.channel.DMChannel) and ctx.channel.id != _COMMANDS_CHANNEL_ID:
    #     await ctx.message.delete()
    #     return
    if timeframe:
        timeframe = Timeframe[timeframe.upper()]
    else:
        timeframe = Timeframe.MONTH

    user_id = ctx.author.id
    guild_id = ctx.guild.id if ctx.guild else _GUILD_ID
    logs = filter_logs(store.get_logs_by_user(guild_id, user_id), timeframe)
    embed = await _user_overview(ctx, user_id, timeframe, logs)
    file = discord.File(f"charts/{user_id}_overview_chart.png", filename=f"{user_id}_overview_chart.png")
    await ctx.send(embed=embed, file=file)


USER_HELP_TEXT = """
Displays a user's overview by timeframe (default:month) [week|month|all]

Examples:
.user 297606972092710913 week
.user 297606972092710913 month
.user 297606972092710913 all
"""


@bot.command(name='user', help=USER_HELP_TEXT)
async def on_message(ctx, user_id: str, timeframe: str = None):
    if timeframe:
        timeframe = Timeframe[timeframe.upper()]
    else:
        timeframe = Timeframe.MONTH

    guild_id = ctx.guild.id
    logs = filter_logs(store.get_logs_by_user(guild_id, user_id), timeframe)
    embed = await _user_overview(ctx, user_id, timeframe, logs)
    file = discord.File(f"charts/{user_id}_overview_chart.png", filename=f"{user_id}_overview_chart.png")
    await ctx.channel.send(embed=embed, file=file)

User = namedtuple('User', ['display_name',])

async def _user_overview(ctx, user_id, timeframe, logs):
    total_points = sum_log_points(logs)
    embed = discord.Embed(title=f"{timeframe.to_ly} Overview".title())
    user = None
    if user_id:
        discord_user = await common.get_member(bot, ctx.guild, user_id)
        display_name = discord_user.display_name if discord_user else 'Unknown'
        user = User(display_name)
    else:
        user = User('TheMoeWay')
    embed.add_field(name='**User**', value=user.display_name)
    embed.add_field(name='**Timeframe**', value=timeframe.value.capitalize())
    embed.add_field(name='**Points**', value=f'{total_points:,g}' or '0')

    pts_by_media_type = calc_points_by_media_type(logs)
    amounts_by_media_type = calc_amounts_by_media_type(logs)

    amounts_by_media_desc = '\n'.join(f'{k.value}: {common.millify(amount)} {_media_type_counter(k)} → {pts_by_media_type[k]:,g} pts'
                                      for k, amount in amounts_by_media_type.items())
    embed.add_field(name='**Breakdown**', value=amounts_by_media_desc or 'None', inline=False)

    generate_trend_graph(user_id, timeframe, logs)
    embed.set_image(url=f"attachment://{user_id}_overview_chart.png")
    # achievements = calc_achievements(amounts_by_media_type)
    # if achievements:
    #     embed.add_field(name='**Achievements**', value='\n'.join(achievements), inline=False)
    return embed



def generate_trend_graph(user_id, timeframe, logs):
    def daterange(start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + timedelta(n)

    points_by_time = defaultdict(lambda: defaultdict(lambda: 0))
    # Start with earliest logs so we don't have to sort the result
    logs = list(reversed(logs))
    start_date, end_date = logs[0].created_at, logs[-1].created_at

    if timeframe == Timeframe.ALL:
        # Set empty months to 0
        for year, month in common.month_year_iter(start_date.month, start_date.year, end_date.month, end_date.year):
            for media_type in reversed(MediaType):
                points_by_time[media_type.value].setdefault((new_date(year, month, 1).strftime("%b/%y")), 0)
        for log in logs:
            points_by_time[log.media_type.value][log.created_at.strftime("%b/%y")] += _to_points(log.media_type, log.amount)

    else:
        # Set empty days to 0
        for media_type in reversed(MediaType):
            for date in daterange(start_date, end_date):
                points_by_time[media_type.value].setdefault(date.date(), 0)
        for log in logs:
            points_by_time[log.media_type.value][log.created_at.date()] += _to_points(log.media_type, log.amount)
        points_by_time = dict(sorted(points_by_time.items()))


    fig, ax = plt.subplots(figsize=(16, 12))
    plt.title(f'{timeframe.to_ly.title()} Overview', fontweight='bold', fontsize=50)
    plt.ylabel('Points', fontweight='bold', fontsize=30)

    print({k: dict(v) for k, v in points_by_time.items()})
    df = pd.DataFrame(points_by_time)
    df = df.fillna(0)
    print(df)

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
    fig.savefig(f"charts/{user_id}_overview_chart.png")



def _achievements_help_text():
    # media_type, ranks
    row_format = '{:>16} ' + '{:>6} ' * (len(ACHIEVEMENTS[MediaType.BOOK]) - 1)
    def row_str(media_type, row):
        return row_format.format(media_type.value + f'({_media_type_counter(media_type)})', *(common.millify(r) for r in row))

    headers = row_format.format('', *(r[:6] for r in ACHIEVEMENT_RANKS))
    table = '\n'.join(row_str(media_type, row) for media_type, row in ACHIEVEMENTS.items())
    total_pts_row = row_format.format('TOTAL POINTS', *PT_ACHIEVEMENTS)
    return f'Displays achievements.\n\n{headers}\n{table}\n{total_pts_row}'


@bot.command(name='achievements', help=_achievements_help_text())
async def on_message(ctx, timeframe: str = None):
    if not isinstance(ctx.channel, discord.channel.DMChannel) and ctx.channel.id != _COMMANDS_CHANNEL_ID:
        await ctx.message.delete()
        return
    if timeframe:
        timeframe = Timeframe[timeframe.upper()]
    else:
        timeframe = Timeframe.ALL

    user_id = ctx.author.id
    guild_id = ctx.guild.id if ctx.guild else _GUILD_ID
    logs = filter_logs(store.get_logs_by_user(guild_id, user_id), timeframe)

    amounts_by_media_type = calc_amounts_by_media_type(logs)
    achievements = calc_achievements(amounts_by_media_type)
    embed = discord.Embed(title=f"{timeframe.to_ly} Achievements".title())
    embed.add_field(name='**Achievements**', value='\n'.join(achievements) if achievements else "None", inline=False)
    await ctx.send(embed=embed)


LEADERBOARD_HELP_TEXT = """
Displays leaderboard by timeframe (default:month) [week|month|all]
First enter a timeframe or a media type. 
If a media type is first entered then no timeframe can be given, making the bot show the default i.e month.
If a timeframe was first entered then you can specify for which media type you want to see the leaderboard of.

Examples:
.leaderboard (displays this month's leaderboard)
.leaderboard manga (display this month's manga leaderboard)
.leaderboard month listening (display this month's listening leaderboard)
.leaderboard all
"""


@bot.command(name='leaderboard', help=LEADERBOARD_HELP_TEXT)
async def on_message(ctx, timeframe_or_media_type: str = None, media_type: str = None):
    start_time = time.time()
    if not isinstance(ctx.channel, discord.channel.DMChannel) and ctx.channel.id != _COMMANDS_CHANNEL_ID:
        await ctx.message.delete()
        return

    timeframe = None
    single_arg = timeframe_or_media_type and not media_type
    if single_arg:
        try:
            timeframe = Timeframe[timeframe_or_media_type.upper()]
        except KeyError:
            if media_type:
                await ctx.message.send(f'Unknown timeframe {timeframe_or_media_type}')
            else:
                timeframe = Timeframe.MONTH
                try:
                    media_type = MediaType[timeframe_or_media_type.upper()]
                except KeyError:
                    await ctx.channel.send(f'Unknown type {timeframe_or_media_type}.')
                    return
    else:
        if timeframe_or_media_type:
            try:
                timeframe = Timeframe[timeframe_or_media_type.upper()]
            except KeyError:
                if media_type:
                    await ctx.message.send(f'Unknown timeframe {timeframe_or_media_type}')
                else:
                    timeframe = Timeframe.MONTH
                    # Parse media
        else:
            timeframe = Timeframe.MONTH

        if media_type:
            try:
                media_type = MediaType[media_type.upper()]
            except KeyError:
                await ctx.channel.send(f'Unknown type {media_type}.')
                return
        else:
            media_type = None

    user_id = ctx.author.id
    guild_id = ctx.guild.id if ctx.guild else _GUILD_ID

    leaderboard = store.get_leaderboard(user_id, timeframe, media_type)

    leaderboard_length = 20
    user_rank = [rank for uid, total, rank in leaderboard if uid == user_id]
    user_rank = user_rank and user_rank[0]


    async def leaderboard_row(user_id, points, rank):
        ellipsis = '...\n' if user_rank and rank == (user_rank-1) and rank > 21 else ''
        user = await common.get_member(bot, ctx.guild, user_id)
        display_name = user.display_name if user else 'Unknown'
        amount = _to_amount(media_type, points) if media_type else points
        return f'{ellipsis}**{make_ordinal(rank)} {display_name}**: {common.millify(amount)}'

    leaderboard_desc = '\n'.join([await leaderboard_row(*row) for row in leaderboard])
    title_args = [
        timeframe.to_ly,
        media_type.value.lower() if media_type else '',
        'leaderboard',
        f'({_media_type_counter(media_type)})' if media_type else '(pts)'
    ]
    title = ' '.join(title_args).title()
    embed = discord.Embed(title=title, description=leaderboard_desc)

    await ctx.channel.send(embed=embed)
    print(f'.leaderboard took {time.time() - start_time:g} secs.')

EXPORT_HELP_TEXT = """
Exports your logs by timeframe (default:all) [week|month|all]

Examples:
.export
.export week
.export month user_id
"""


@bot.command(name='export', help=EXPORT_HELP_TEXT)
async def on_message(ctx, timeframe: str = None, user_id: str = None):
    if timeframe:
        timeframe = Timeframe[timeframe.upper()]
    else:
        timeframe = Timeframe.ALL

    guild_id = ctx.guild.id
    if not user_id:
        user_id = ctx.author.id
    await _export(ctx, guild_id, user_id, timeframe)


async def _export(ctx, guild_id, user_id, timeframe):
    logs = filter_logs(store.get_logs_by_user(guild_id, user_id), timeframe)

    tmp = tempfile.NamedTemporaryFile()
    with open(tmp.name, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['discord_guild_id', 'discord_user_id',
                         'media_type', 'amount', 'note', 'created_at'])
        writer.writerows(logs)

    await ctx.send(file=discord.File(tmp.name, filename=f'{user_id}_{timeframe.value}.csv'))

LOGS_HELP_TEXT = """
Displays your logs by timeframe (default:month) [week|month|all]

Examples:
.logs user_id
.logs week
.logs month
.logs user_id week
"""


@bot.command(name='logs', help=LOGS_HELP_TEXT)
async def on_message(ctx, user_id_or_timeframe: str = None, timeframe: str = None):
    if not isinstance(ctx.channel, discord.channel.DMChannel) and ctx.channel.id != _COMMANDS_CHANNEL_ID:
        await ctx.message.delete()
        return
    user_id = None
    if not user_id_or_timeframe:
        timeframe = Timeframe.MONTH
        user_id = ctx.author.id
    elif user_id_or_timeframe and not timeframe:
        try:
            timeframe = Timeframe[user_id_or_timeframe.upper()]
            user_id = ctx.author.id
        except KeyError:
            user_id = user_id_or_timeframe
            timeframe = Timeframe.MONTH
    else:
        user_id = user_id_or_timeframe
        timeframe= Timeframe[timeframe.upper()]

    guild_id = ctx.guild.id if ctx.guild else _GUILD_ID

    logs = filter_logs(store.get_logs_by_user(guild_id, user_id), timeframe)
    if not logs:
        await ctx.send("No logs found")
        return
    max_logs = 20
    def gen_desc(logs, max_logs):
        desc = '\n'.join(format_log(log) for log in logs[:max_logs])
        if len(logs) > max_logs:
            too_many_logs = (
                f'...({len(logs) - max_logs} more logs)...\n'
                f'Specify a smaller timeframe or use `.export` to see them all\n'
            )
        else:
            too_many_logs = ''
        return f'```\n{desc}\n{too_many_logs}```'

    max_logs = 20
    log_desc = gen_desc(logs, max_logs)
    while len(log_desc) > 2000:
        max_logs -= 1
        log_desc = gen_desc(logs, max_logs)
    await ctx.send(log_desc)


@bot.command(name='remove_user', help="Remove a user and clear their logs")
async def on_message(ctx, member: discord.Member):
    if not common.has_role(ctx.author, _ADMIN_ROLE_IDS):
        await ctx.send("You don't have perms to do this")
        return

    guild_id, user_id = ctx.guild.id, member.id
    await _export(ctx, guild_id, user_id, Timeframe.ALL)

    store.delete_user_logs(ctx.guild.id, member.id)
    await ctx.send('Deleted user')


def _to_points(media_type: MediaType, amount):
    if media_type == MediaType.BOOK:
        return amount
    elif media_type == MediaType.MANGA:
        return amount * 0.2
    elif media_type == MediaType.VN:
        return amount / 350.0
    elif media_type == MediaType.ANIME:
        return amount * 9.5
    elif media_type == MediaType.LISTENING:
        return amount * 0.45
    elif media_type == MediaType.READTIME:
        return amount * 0.45
    elif media_type == MediaType.READING:
        return amount / 350.0
    else:
        raise Exception(f'Unknown media type: {media_type}')

def _to_amount(media_type: MediaType, points):
    if media_type == MediaType.BOOK:
        return points
    elif media_type == MediaType.MANGA:
        return points * 5
    elif media_type == MediaType.VN:
        return points * 350.0
    elif media_type == MediaType.ANIME:
        return points / 9.5
    elif media_type == MediaType.LISTENING:
        return points / 0.45
    elif media_type == MediaType.READTIME:
        return points / 0.45
    elif media_type == MediaType.READING:
        return points * 350.0
    else:
        raise Exception(f'Unknown media type: {media_type}')


def media_type_converter_help(media_type):
    if media_type == MediaType.BOOK:
        return '1 point per page'
    elif media_type == MediaType.MANGA:
        return '0.2 points per page'
    elif media_type == MediaType.VN:
        return '1/350 points/character'
    elif media_type == MediaType.ANIME:
        return '9.5 points per episode'
    elif media_type == MediaType.LISTENING:
        return '0.45 points/min of listening'
    elif media_type == MediaType.READTIME:
        return '0.45 points/min of reading time'
    elif media_type == MediaType.READING:
        return '1/350 points/character of reading'
    else:
        raise Exception(f'Unknown media type: {media_type}')


def filter_logs(logs, tf, media_type = None):
    now = datetime.now()
    tf_logs = None
    if tf == Timeframe.WEEK:
        last_week = now - timedelta(days=8)
        tf_logs = [l for l in logs if l.created_at > last_week]
    elif tf == Timeframe.MONTH:
        tf_logs = [l for l in logs if l.created_at.month == now.month and l.created_at.year == now.year]
    elif tf == Timeframe.ALL:
        tf_logs = logs
    else:
        raise Exception(f'Unknown timeframe {tf}')

    if not media_type:
        return tf_logs
    else:
        return [l for l in tf_logs if l.media_type == media_type]


def group_logs_by_user_id(logs):
    res = defaultdict(list)
    for log in logs:
        res[log.discord_user_id].append(log)
    return res


def group_logs_by_media_type(logs):
    res = defaultdict(list)
    for log in logs:
        res[log.media_type].append(log)
    return res


def sum_log_points(logs):
    return sum(_to_points(l.media_type, l.amount) for l in logs)


def calc_points_by_media_type(logs):
    return {k: sum_log_points(logs) for k, logs in group_logs_by_media_type(logs).items()}


def calc_amounts_by_media_type(logs):
    return {k: sum(l.amount for l in logs) for k, logs in group_logs_by_media_type(logs).items()}

def calc_achievements(amount_by_media_type):
    abmt = amount_by_media_type
    # Combine Book and Reading
    if MediaType.BOOK in abmt or MediaType.READING in abmt:
        abmt[MediaType.BOOK] = abmt.get(MediaType.BOOK, 0) + abmt.get(MediaType.READING, 0) / 350.0
        abmt.pop(MediaType.READING, None)

    achievements = []

    def get_index_by_ranges(amount, ranges):
        # if amount < ranges[0]:
        #     return 0
        for i, (lower, upper) in enumerate(pairwise(ranges)):
            if lower <= amount < upper:
                return i
        else:
            return -1

    # Media specific achievements
    for media_type, amount in abmt.items():
        index = get_index_by_ranges(amount, ACHIEVEMENTS[media_type])
        achievement = (
            f'{ACHIEVEMENT_EMOJIS[index]} {media_type.value.title()} {ACHIEVEMENT_RANKS[index]}: {common.millify(amount)} '
            f'({common.millify(ACHIEVEMENTS[media_type][index])} - {common.millify(ACHIEVEMENTS[media_type][index+1])} '
            f'{_media_type_counter(media_type)})'
        )
        achievements.append(achievement)

    # Point specific achievements
    total_points = sum(_to_points(media_type, amount) for media_type, amount in abmt.items())
    index = get_index_by_ranges(total_points, PT_ACHIEVEMENTS)
    immersion_achievement = (
        f'{ACHIEVEMENT_EMOJIS[index]} Immersion {ACHIEVEMENT_RANKS[index]}: {total_points:,g} '
        f'({PT_ACHIEVEMENTS[index]:,} - {PT_ACHIEVEMENTS[index+1]:,} pts)'
    )
    achievements.append(immersion_achievement)

    return achievements


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)



def format_log(log):
    return (
        f"{log.created_at.strftime('%Y-%m-%d')}: {log.media_type.value} "
        f"{log.amount:,g} {_media_type_counter(log.media_type)} → {_to_points(log.media_type, log.amount):,g}pts: {log.note}"
    )

bot.run('TOKEN')

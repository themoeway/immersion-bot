import asyncio
import discord
from enum import Enum
import random
import sqlite3
import math


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


def has_role(user, valid_roles):
    return any(r.id in valid_roles for r in user.roles)

TMW_GUILD_ID = 617136488840429598
EMOJI_TABLE = {
    # 'Yay': 658999234787278848,
    # 'NanaYes': 837211260155854849,
    # 'NanaYay': 837211306293067797,
    "990": 921933172432863283,
    "AYAYA": 848256559191687168,
    "Angry": 688824902823706634,
    "AnyaHeh": 855296982812983336,
    "AnyaSweat": 854990671613788170,
    "ArisuScream": 921872320375709747,
    "CatBlush": 933089264030339083,
    "CatRage": 936524311911600199,
    "CatTup": 948511239401799681,
    "ChikaTup": 918620369919828000,
    "ChikaYada": 918622997051486298,
    "ChubbyGero": 831348462305673286,
    "ChubbyGeroSwag": 929124878047641690,
    "Chuui": 872352719917187133,
    "CoolCat": 783741575582580758,
    "HillingGakkari": 928130226410651688,
    "InuPero": 963127794194350110,
    "KannaShoot": 678245463270490153,
    "KimoiHuh": 931588710473031761,
    "MakotoSad": 888194443134504990,
    "NadeshikoUma": 921677406849363989,
    "NanaCry": 877678258332782642,
    "NanaJam": 882894763987177493,
    "NanaSleep": 877678937940058172,
    "NanaThink": 837209897706848266,
    "NanaTired": 877678949130436658,
    "NanaYay": 837211306293067797,
    "NanaYes": 877679734547427349,
    "NekoGero": 936524524231458897,
    "NicoDab": 783746864138420254,
    "NicoShy": 678245454823030784,
    "NicoSmile": 783744823281713192,
    "NicoSmug": 783747913808609300,
    "PainPeko": 848260032407535636,
    "Peek": 918616198302793739,
    "PensiveCat": 783736784168681493,
    "PensiveMonke": 783736811641503754,
    "RageGero": 831361358259683350,
    "RengeShrug": 826485174312763422,
    "RoxyKowai": 914943594555641866,
    "RubyCry": 918622902440575017,
    "RubyPigiii": 918622959906742273,
    "ShimarinDango": 921677567084359702,
    "SorryGero": 831361306098794518,
    "SugoiAA": 678245454068056097,
    "TachiSmile": 688824520362164303,
    "TohruFlex": 926637533994037328,
    "TohruShrug": 827049208275009537,
    "Yay": 658999234787278848,
    "YouWaitWhat": 918622871700504577,
    "Yousoroo": 698293340881289221,
    "Yousoroo2": 709339172602904586,
    "YuiPeace": 918623813552447529,
    "YuiShrug": 827051628347654164,
    "ajatt": 783749154807087134,
    "akkoShrug": 688824479220105231,
    "anki": 688802971089371185,
    "baka": 848256505852985394,
    "bakalisten": 937213856407777360,
}

def emoji(s):
    return f'<:{s}:{EMOJI_TABLE[s]}>'


def random_emoji():
    return emoji(random.choice(list(EMOJI_TABLE)))


def mention(user_id):
    return f'<@!{user_id}>'


user_cache = {}
async def get_member(bot, guild, user_id):
    get_method = guild.get_member if guild else bot.get_user
    fetch_method = guild.fetch_member if guild else bot.fetch_user
    if user_id in user_cache:
        print('user_cache')
        return user_cache[user_id]
    user = get_method(user_id)
    if user:
        print('guild.get_member')
        user_cache[user_id] = user
        return user
    try:
        user = await fetch_method(user_id)
    except discord.NotFound:
        print(f'Unknown user {user_id}')
        return None
    user_cache[user_id] = user
    return user

millnames = ['','k','m','b']

def millify(n):
    n = float(n)
    if n == float('inf'):
        return 'inf'
    if n < 10_000:
        return f'{n:,g}'
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.2f}{}'.format(n / 10**(3 * millidx), millnames[millidx])


def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return f'{n}{suffix}'


def month_year_iter(start_month, start_year, end_month, end_year):
    ym_start= 12 * start_year + start_month - 1
    ym_end= 12 * end_year + end_month - 1
    for ym in range(ym_start, ym_end):
        y, m = divmod(ym, 12)
        yield y, m+1
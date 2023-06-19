import sqlite3
from collections import namedtuple
from enum import Enum

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
    ANYTHING = 'ANYTHING' # ANYTHING as an option for setting a point goal

def namedtuple_factory(cursor, row):
    """Returns sqlite rows as named tuples."""
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    res = Row(*row)
    # HACK:
    if hasattr(res, 'media_type'):
        return res._replace(media_type=MediaType[res.media_type])
    return res

class Store:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = namedtuple_factory
    
    def new_log(
        self, discord_guild_id, discord_user_id, media_type, amount, note, created_at
    ):
        with self.conn:
            self.conn.execute("INSERT INTO logs (discord_guild_id, discord_user_id, media_type, amount, note, created_at)VALUES (?,?,?,?,?,?)", (int(discord_guild_id), int(discord_user_id), str(media_type), int(amount), str(note), str(created_at)))
            
    def current_points(self, discord_guild_id, discord_user_id, created_at):
        with self.conn:
            query = f"""
            SELECT SUM(amount) as sum_amount FROM logs
            WHERE discord_guild_id=? AND discord_user_id=? AND created_at BETWEEN '{created_at[0]}' AND '{created_at[1]}'
            """
            
            data = (discord_guild_id, discord_user_id)
            cursor = self.conn.cursor()
            cursor.execute(query, data)
            return cursor.fetchall()
        
    def get_leaderboard(self, discord_user_id, timeframe, media_type):
        with self.conn:
            if media_type:
                where_clause = f"WHERE media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[1]}' AND '{timeframe[2]}'"""
            else:
                where_clause = f"WHERE created_at BETWEEN '{timeframe[1]}' AND '{timeframe[2]}'"""
            
            query = f"""
            WITH scoreboard AS (
                SELECT
                    discord_user_id,
                    SUM(
                    CASE
                        WHEN media_type = 'BOOK' THEN amount
                        WHEN media_type = 'MANGA' THEN amount * 0.2
                        WHEN media_type = 'VN' THEN amount * (1.0 / 350.0)
                        WHEN media_type = 'ANIME' THEN amount * 9.5
                        WHEN media_type = 'READING' THEN amount * (1.0 / 350.0)
                        WHEN media_type = 'READTIME' THEN amount * 0.45
                        WHEN media_type = 'LISTENING' THEN amount * 0.45
                        ELSE 0
                    END
                    ) AS total
                FROM logs
                {where_clause}
                GROUP BY discord_user_id
                ), leaderboard AS (
                SELECT
                    discord_user_id,
                    total,
                    RANK () OVER (ORDER BY total DESC) AS rank
                FROM scoreboard
                )
                SELECT * FROM leaderboard
                WHERE (
                rank <= 20
                ) OR (
                rank >= (SELECT rank FROM leaderboard WHERE discord_user_id = ?) - 1
                AND
                rank <= (SELECT rank FROM leaderboard WHERE discord_user_id = ?) + 1
                );
            """
            data = (discord_user_id, discord_user_id)
            cursor = self.conn.cursor()
            cursor.execute(query, data)
            return cursor.fetchall()
    
    def get_logs_by_user(self, discord_user_id, media_type, timeframe):
        if media_type == None and timeframe == None:
            where_clause = f"discord_user_id={discord_user_id}"
        if media_type and media_type != None and timeframe:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif not media_type and media_type != None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}'"""
        elif media_type == None and timeframe:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        
        query = f"""
        SELECT * FROM logs
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def get_recent_goal_alike_logs(self, discord_user_id, timeframe):
        where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""

        query = f"""SELECT media_type, SUM(amount) as da, note FROM logs
        WHERE {where_clause}
        GROUP BY media_type, note
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
        
    def get_log_streak(self, discord_user_id):
        return
#         query = f"""SELECT created_at,
# ROW_NUMBER() OVER (ORDER BY created_at) as RN
# from logs WHERE discord_user_id={discord_user_id}"""

#         query = f"""WITH
 
#           -- This table contains all the distinct date 
#           -- instances in the data set
#           dates(date) AS (
#             SELECT DISTINCT CAST(created_at AS DATE)
#             FROM logs
#             WHERE discord_user_id={discord_user_id}
#           ),

#           -- Generate "groups" of dates by subtracting the
#           -- date's row number (no gaps) from the date itself
#           -- (with potential gaps). Whenever there is a gap,
#           -- there will be a new group
#           groups AS (
#             SELECT
#               ROW_NUMBER() OVER (ORDER BY date) AS rn,
#               dateadd(day, -ROW_NUMBER() OVER (ORDER BY date), date) AS grp,
#               date
#             FROM dates
#           )
#         SELECT
#           COUNT(*) AS consecutiveDates,
#           MIN(date) AS minDate,
#           MAX(date) AS maxDate
#         FROM groups
#         GROUP BY grp
#         ORDER BY 1 DESC, 2 DESC"""

    
#         print(query)
#         cursor = self.conn.cursor()
#         cursor.execute(query)
#         return cursor.fetchall()

class Set_Goal:
    def __init__(self, db_name):
            self.conn = sqlite3.connect(
                db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = namedtuple_factory
    
    def new_goal(self, discord_user_id, goal_type, media_type, amount, text, span, created_at, end):
        with self.conn:
            query = """
            INSERT INTO goals (discord_user_id, goal_type, media_type, amount, text, span, created_at, end)
            VALUES (?,?,?,?,?,?,?,?);
            """
            data = (discord_user_id, goal_type, media_type, amount, text, span, created_at, end)
            self.conn.execute(query, data)
            
    def get_goals(self, discord_user_id):
        where_clause = f"""discord_user_id={discord_user_id}"""
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at ASC;
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def check_goal_exists(self, discord_user_id, goal_type, media_type, text):
        print(discord_user_id, goal_type, media_type, text)
        query = f"""SELECT EXISTS(
            SELECT * FROM goals WHERE discord_user_id=? AND goal_type=? AND media_type=? AND text LIKE ?
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query, [discord_user_id, goal_type, media_type, text])
        return cursor.fetchall()[0][0] == 1
    
    def delete_goal(self, discord_user_id, media_type, amount, span):
        where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND amount={amount} AND span='{span}'"
        query = f"""
        DELETE FROM goals WHERE {where_clause}"""
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
       
    def get_one_goal(self, discord_user_id, media_type, amount, span):
        where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND amount={amount} AND span='{span}'"
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

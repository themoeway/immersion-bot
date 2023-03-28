# immersion-bot
TMW's immersion bot

The old bot i.e current bot is run with the immersion_bot.py file, common.py and db.py are essential since they provide helpers/modifiers for the bot.

The new bot i.e slash bot is started with launch_bot.py. One command for one file in cogs, so for instance, the feature of logging your immersion via /log is in it's respective file log.py under the cogs directory. 

The datebase prod is needed to save every log. 

db.py manages all sql queries. common.py is also a helper.

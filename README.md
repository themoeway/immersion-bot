# immersion-bot

TMW's immersion bot

## Setup

- Check `requirements.txt`, install via `pip install -r requirements.txt` (recommended in venv)
- Enter bot token in token_net.txt
- `cogs/log.py` l.44 change `channel_id` to your immersion_logs channel
- `cogs/leaderboard.py` l.38 change `channel_id` to your immersion_logs channel
- `cogs/jsons/settings.json` change `guildId`

You need both prod.db and goals.db

TODO: Move constants to a constants.py file or read from environment variables

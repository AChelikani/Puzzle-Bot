# Puzzle-Bot
A slack bot for helping manage submissions, hints, and scores in a puzzle hunt.


### Set-up for Development
Create file `config.py` and put your bot access token into it like this:
```
BOT_ACCESS_TOKEN = <bot_access_token>
```

Run `python bot.py` to run. Bot only works on DMs because we don't want people
publicly messaging the bot.

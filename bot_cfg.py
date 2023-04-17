from os import getenv

tg_api_hash = getenv("TG_API_HASH", None)
tg_api_id = int(getenv("TG_API_ID", None))
tg_bot_token = getenv("TG_BOT_TOKEN", None)
render_web_port = getenv("PORT", "8080")
render_url = getenv("RENDER_EXTERNAL_HOSTNAME", "placeholder")
bot_users = getenv("USERS_ALLOWED").split()

# fmt: off
from logging import basicConfig, log, INFO, WARN, ERROR, CRITICAL
from pathlib import Path
from random import randbytes
from requests import get
from urllib.parse import quote, unquote
from threading import current_thread
from ctypes import c_ulong, pythonapi, py_object
from typing import Any, Awaitable, Callable
import asyncio

basicConfig(format="[%(levelname)s]: %(message)s", level=INFO, force=True)
log(INFO, "Initializing...")
# fmt: on

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram.enums.parse_mode import ParseMode
from os import system, unlink
from inspect import iscoroutinefunction
from time import sleep, time
import bot_cfg


def async_e(func: Callable) -> Awaitable:
    """Decorate a sync function to be used as async. Supports task cancelling.
    This version is based on loop.run_in_executor()
    """

    async def run_cancellable(*args, **kwargs) -> Any:
        def worker() -> Any:
            context["thread"] = current_thread().ident
            return func(*args, **kwargs)

        context: dict = {"thread": None}
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        future: asyncio.Future = asyncio.ensure_future(
            loop.run_in_executor(None, worker)
        )
        while not future.done():
            try:
                await asyncio.wait([future])
            except asyncio.CancelledError:
                thread_id: c_ulong = c_ulong(context["thread"])
                exception: py_object = py_object(asyncio.CancelledError)
                ret: int = pythonapi.PyThreadState_SetAsyncExc(thread_id, exception)
                if ret > 1:  # This should NEVER happen, but shit happens
                    pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
        return future.result()

    return run_cancellable


def slow(interval: int):
    def dec(func):
        last_update = [
            time()
        ]  # It needs to be mutable from the wrapper, hence the list

        # Sync wrapper
        def wrap_sync(*args, **kwargs):
            now = time()
            if now - last_update[0] < interval:
                return
            last_update[0] = now
            return func(*args, **kwargs)

        # Async wrapper
        async def wrap_async(*args, **kwargs):
            now = time()
            if now - last_update[0] < interval:
                return
            last_update[0] = now
            return await func(*args, **kwargs)

        if iscoroutinefunction(func):
            return wrap_async
        else:
            return wrap_sync

    return dec


bot: Client = Client(
    "bot",
    api_id=bot_cfg.tg_api_id,
    api_hash=bot_cfg.tg_api_hash,
    bot_token=bot_cfg.tg_bot_token,
)
bot.set_parse_mode(ParseMode.DISABLED)


@slow(2)
async def progress_bar(current: int, total: int, progress_msg: Message):
    try:
        await progress_msg.edit_text(f"⏳ Descargando... {(100 * current // total)}%")
    except:
        pass


@bot.on_message(filters.command("start") & filters.private)
async def welcome(client: Client, message: Message):
    await message.reply("Bienvenido")


@bot.on_message(filters.media & filters.private)
async def download_media(client: Client, message: Message):
    if not (message.from_user.username in bot_cfg.bot_users):
        log(WARN, f"UNAUTHORIZED: {message.from_user.username}({message.from_user.id})")
        return

    log(INFO, f"Downloading: {message.media.name}")
    progress_msg: Message = await message.reply("⏳ Descargando... 0%", quote=True)
    try:
        fpath = await message.download(
            file_name=f"./downloads/{randbytes(1).hex()}/",
            progress=progress_bar,
            progress_args=(progress_msg,),
        )
    except:
        log(ERROR, f"Error downloading: {message.media.name}")
        try:
            await progress_msg.edit("❌ Error durante la descarga.")
        except:
            pass
        return

    fpath = Path(fpath)
    url = f"https://{bot_cfg.render_url}/{fpath.parent.name}/{quote(fpath.name)}"
    log(INFO, f"Downloaded: {url}")
    try:
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Eliminar", "delete")]])
        await progress_msg.edit(
            url, reply_markup=buttons, disable_web_page_preview=True
        )
    except:
        pass


@bot.on_callback_query(filters.regex(r"^delete$"))
async def delete(client: Client, query: CallbackQuery):
    url = Path(unquote(query.message.text))
    fpath = f"./downloads/{url.parent.name}/{url.name}"
    log(INFO, f"Delete: {fpath}")
    await query.answer("Eliminando...")
    try:
        unlink(fpath)
        await query.message.delete()
    except:
        pass


@async_e
def webserver():
    log(INFO, f"Starting webserver on {bot_cfg.render_web_port}")
    system(f"python -m http.server -d ./downloads/ {bot_cfg.render_web_port}")
    # run(["python", "-m", "http.server", "-d", "./downloads/", bot_cfg.fly_web_port])


@async_e
def heartbeat():
    log(INFO, "Starting heartbeat each 10 minutes")
    while True:
        try:
            log(INFO, "Heartbeat")
            get(f"https://{bot_cfg.render_url}/HEARTBEAT/")

        except:
            pass

        sleep(10 * 60)


log(INFO, "Starting...")
bot.loop.create_task(webserver())
bot.loop.create_task(heartbeat())
bot.run()

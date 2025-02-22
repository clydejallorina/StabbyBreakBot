from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Optional, NoReturn
import asyncio
import os
import logging

from aiohttp import ClientSession
from dotenv import load_dotenv
from PIL import Image, ImageFile
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, CodeFlow
from twitchAPI.type import AuthScope
from twitchAPI.chat import Chat, ChatEvent, EventData, JoinedEvent

from ocr import check_if_string_in_image

load_dotenv()

TWITCH_APP_ID = os.getenv("TWITCH_APP_ID")
TWITCH_APP_SECRET = os.getenv("TWITCH_APP_SECRET")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "stabbystabby")
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.USER_BOT, AuthScope.CHANNEL_BOT]
TARGET_TEXT = os.getenv("TARGET_TEXT", "!brb")

twitch: Twitch
chat: Chat
last_thumbnail: ImageFile.ImageFile
last_check_status: bool = False

# TODO: Maybe don't depend on stream thumbnails to catch the !brbs
#       It could be a very short break.
#       Might be worth looking into streamlink

async def on_ready(ready_event: EventData):
    logging.info("Chat client ready! Attempting to join %s's channel...", TARGET_CHANNEL)
    await ready_event.chat.join_room(TARGET_CHANNEL)


async def on_channel_joined(event: JoinedEvent):
    logging.info("Successfully joined %s as %s", event.room_name, event.user_name)


async def download_stream_thumbnail(url: str) -> Optional[bytes]:
    if url.endswith("-{width}x{height}.jpg"):
        url = url.replace("-{width}x{height}.jpg", "-1920x1080.jpg")
    logging.debug("Downloading %s", url)
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
    return None


async def get_stream_thumbnail() -> Optional[ImageFile.ImageFile]:
    global twitch
    global last_thumbnail
    async for stream in twitch.get_streams(first=1, user_login=[TARGET_CHANNEL]):
        # First break check
        try:
            stream_time_elapsed = datetime.now(tz=timezone.utc) - stream.started_at
            if stream_time_elapsed.total_seconds() >= 3600 and stream_time_elapsed.total_seconds() < 3600 + 120:
                # Immediately send the break message if the stream has already been running for an hour
                # Make sure that it doesn't get triggered after it's already done so
                # TODO: Move this logic somewhere else where it makes sense
                #       Maybe move the stream-get functionality to another async function?
                logging.info("It's time for the first break!")
                await send_chat_message(0)
        except Exception as e:
            logging.exception(e)
        if stream.thumbnail_url != "":
            thumbnail = await download_stream_thumbnail(stream.thumbnail_url)
            if thumbnail != None:
                last_thumbnail = Image.open(BytesIO(thumbnail))
                logging.debug("Successfully obtained stream thumbnail for %s", TARGET_CHANNEL)
                return last_thumbnail
            else:
                logging.error("Could not obtain stream thumbnail for %s (stream thumbnail download failed)", TARGET_CHANNEL)
        else:
            logging.error("Could not obtain stream thumbnail for %s (no thumbnail URL)", TARGET_CHANNEL)
    return None


async def stream_thumbnail_task() -> NoReturn:
    global last_thumbnail
    global last_check_status
    
    while True:
        logging.info("Attempting to get stream thumbnail for %s", TARGET_CHANNEL)
        thumbnail = await get_stream_thumbnail()
        if thumbnail != None and TARGET_TEXT != "":
            has_text = check_if_string_in_image(TARGET_TEXT, thumbnail)
            logging.debug("Does thumbnail have text?: %s", str(has_text))
            if last_check_status != has_text and not has_text:
                # Start timer once we have detected that the text in the thumbnail is gone
                logging.debug("Sending timer task...")
                asyncio.get_event_loop().create_task(send_chat_message())
            last_check_status = has_text
        # Poll Twitch API every 2 minutes
        await asyncio.sleep(60 * 2)


async def send_chat_message(delay: int = 3600):
    logging.debug("Started timer task with a delay of %d", delay)
    if delay > 0:
        await asyncio.sleep(delay)
    logging.debug("Timer ended")
    # commented this out so we don't send a message during debugging lol
    # chat.send_message(TARGET_CHANNEL, "Mayhaps it is time for a break?")


async def run():
    global twitch
    global chat
    global TWITCH_APP_ID
    global TWITCH_APP_SECRET
    global USER_SCOPE
    
    load_dotenv()

    TWITCH_APP_ID = os.getenv("TWITCH_APP_ID")
    TWITCH_APP_SECRET = os.getenv("TWITCH_APP_SECRET")
    
    if TWITCH_APP_ID == None or TWITCH_APP_SECRET == None:
        logging.error("Twitch App ID or Secret are not set! (None)")
        return
    if TWITCH_APP_ID == "" or TWITCH_APP_SECRET == "":
        logging.error("Twitch App ID or Secret are not set! (Empty string)")
        return
    
    twitch = await Twitch(
        app_id=TWITCH_APP_ID,
        app_secret=TWITCH_APP_SECRET,
        target_app_auth_scope=USER_SCOPE,
    )
    code_flow = CodeFlow(twitch, USER_SCOPE)
    code, url = await code_flow.get_code()
    # TODO: Generate implicit code that can be used for a long while.
    print("Visit this URL while logged in to the bot account to connect the account:", url)
    access_token, refresh_token = await code_flow.wait_for_auth_complete()
    await twitch.set_user_authentication(access_token, USER_SCOPE, refresh_token)
    
    chat = await Chat(twitch, initial_channel=[TARGET_CHANNEL])
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.JOINED, on_channel_joined)
    chat.start()
    
    loop = asyncio.get_event_loop()
    thumbnail_task = loop.create_task(stream_thumbnail_task())
    
    logging.info("Setup complete")
    
    try:
        while True:
            # Just throwing this in here so this stays alive
            # until an error happens or something
            await asyncio.sleep(100)
    finally:
        chat.stop()
        thumbnail_task.cancel()
        await twitch.close()

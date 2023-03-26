import requests
import os

YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3/'
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
MISSING_USER_ERROR = 'Please join a voice channel with NEØN to use this command.'


class YTParser:
    def __init__(self, url):
        self.request_url = f"{YOUTUBE_API_URL}search?key={YOUTUBE_API_KEY}" \
                           f"&regionCode=US&type=video&part=snippet&q={url}&maxResults=1"

    async def parse(self):
        # This function will parse a title or URL and return a tuple with the URL and title.

        youtube_api_response = requests.get(self.request_url)

        if youtube_api_response.status_code != 200:
            return None

        data = youtube_api_response.json()

        if len(data['items']) == 0:
            return None

        video_title = data['items'][0]['snippet']['title']
        video_id = data['items'][0]['id']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        video_info = (video_url, video_title)
        return video_info


async def status_check(ctx, bot_voice):
    if not ctx.message.author.voice:
        await ctx.send(MISSING_USER_ERROR)
        return False

    users_channel = ctx.message.author.voice.channel
    if not bot_voice:
        await users_channel.connect()
        return True
    if users_channel != bot_voice.channel:
        await ctx.send(MISSING_USER_ERROR)
        return False
    return None

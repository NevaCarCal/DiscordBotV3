# This bot is created to be a better, cleaner, faster version of my old bot.

import asyncio
import json
import os
import random
import time
import requests
import yt_dlp

import discord
from discord import Embed
from discord.ext import commands
from DiscordBotModules import YTParser, status_check
from BotClasses import APIsFluff, MusicPlayer

# Here, all global constants are defined.
WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'
RANDOM_URL = "https://some-random-api.ml"

YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3/'
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
DISCORD_API_KEY = os.environ.get('DISCORD_API_KEY')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
MISSING_USER_ERROR = 'Please join a voice channel with NEØN to use this command.'
MISSING_BOT_ERROR = 'NEØN is not in a voice channel.'
AVAILABLE_ANIMAL_FACTS = ('dog', 'cat', 'panda', 'fox', 'bird', 'koala', 'kangaroo', 'red_panda',)
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}
YDL_PARAMS = {
    'format': 'bestaudio',
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3'
    }],
}


def main():
    intents = discord.Intents.all()
    intents.members = True
    now_playing, looping = [], False

    client = commands.Bot(command_prefix='€', description="NEØN is constantly being worked on!",
                          intents=intents, help_command=None)
    client.remove_command('help')

    @client.event
    async def on_ready():
        # Here, we set NEØN's username and status.
        await client.user.edit(username="NEØN")
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                               name=""))

        print("{0.user} is ready!".format(client))

        queue_data = {}
        json.dump(queue_data, open("queue.json", "w"))

    async def get_animal(request_url, context):
        # This function retrieves a random animal fact from the API and handles its data.

        animal_data = requests.get(request_url)
        if animal_data.status_code != 200:
            await context.send(f"Something went wrong. Error code is {animal_data.status_code}")
            return

        json_data = json.loads(animal_data.text)
        image_url = json_data['image']
        fact = json_data['fact']
        # Here we turn the returned info from the API into a JSON file, which we'll use to get the image and fact.

        if not image_url:
            await context.send(fact)
        elif image_url:
            embed = Embed().set_image(url=image_url)
            await context.send(fact, embed=embed)

    @client.command(aliases=['f', 'fact'])
    async def on_fact(ctx, animal=None, colour=None):
        # This function handles different scenarios when the user calls the fact command.

        if animal:
            animal = animal.lower()
        animal_url = f"{RANDOM_URL}/animal/{animal}"

        if not animal:
            animal_url = f"{RANDOM_URL}/animal/{random.choice(AVAILABLE_ANIMAL_FACTS)}"
            await get_animal(animal_url, ctx)
        elif animal in AVAILABLE_ANIMAL_FACTS and not colour:
            await get_animal(animal_url, ctx)
        elif animal == 'red' and colour == 'panda':
            animal_url = f"{RANDOM_URL}/animal/red_panda"
            await get_animal(animal_url, ctx)
        elif animal not in AVAILABLE_ANIMAL_FACTS:
            await ctx.send(f"Sorry, I don't know about {animal} facts.")

    @client.command(aliases=['w', 'weather'])
    async def on_weather(ctx, city: str, unit_system='metric'):
        # This function will handle the API data as well as user commands.

        unit_system = unit_system.lower()
        city = city.lower()
        if unit_system == 'imperial' or unit_system == 'fahrenheit':
            temp_unit = '°F'
            unit_system = 'imperial'
        else:
            temp_unit = '°C'
            unit_system = 'metric'

        weather_data = requests.get(f"{WEATHER_API_URL}?q={city}&appid={WEATHER_API_KEY}&units={unit_system}")

        if weather_data.status_code != 200:
            await ctx.send(f"Something went wrong. Error code is {weather_data.status_code}")
            return

        data = weather_data.json()
        weather = data['weather'][0]['description']
        temperature = data['main']['temp']
        weather_response = f"The weather in {city} is {weather}.\n " \
                           f"The temperature in {city} is {temperature}{temp_unit}."
        await ctx.send(weather_response)

    @client.command(aliases=['p', 'play'])
    async def on_play(ctx, *user_url: str):
        # This function will handle all related to playing music and its queue.
        user_url = '_'.join(user_url)
        guild_id = str(ctx.guild.id)
        queue_data = json.load(open("queue.json"))
        bot_voice = ctx.guild.voice_client

        async def music_player(video_info, silent=False):
            # This function handles the music player and audio.
            url_to_play = video_info[0]
            video_title = video_info[1]

            if bot_voice.is_playing() or bot_voice.is_paused():
                if not silent:
                    await ctx.send(f"**Added to queue:** {video_title}")
                queue_data[guild_id].append(video_info)
                json.dump(queue_data, open("queue.json", "w"))
                await queue_loop()
                return

            with yt_dlp.YoutubeDL(YDL_PARAMS) as ydl:
                info = ydl.extract_info(url_to_play, download=False, process=True, extra_info={'noplaylist': True})

                if '&list' in url_to_play:
                    info = ydl.extract_info(url_to_play, download=False, process=True, extra_info={'noplaylist': False})
                    info = info['entries'][0]

            url = info['url']

            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), volume=0.15)
            embed = discord.Embed(title=f"**Now playing:** {video_title}", color=0x3D85C6, url=url_to_play)

            if not bot_voice.is_playing() and not bot_voice.is_paused():
                bot_voice.play(source)
                await ctx.send(embed=embed)
                now_playing.clear()
                now_playing.append(video_title)

        async def queue_loop():
            # This handles the actual functionality of the queue

            while len(queue_data[guild_id]) != 0:
                counter = 0
                while counter < 2:
                    if not bot_voice.is_playing() and not bot_voice.is_paused():
                        await asyncio.sleep(0.6)
                        counter += 1
                    else:
                        await asyncio.sleep(1.4)
                        counter = 0
                if counter >= 2:
                    try:
                        live_file = json.load(open("queue.json"))
                        video_data = live_file[guild_id][0]
                        await music_player(video_data)
                        del live_file[guild_id][0]
                        json.dump(live_file, open("queue.json", "w"))
                    except IndexError:
                        time.sleep(2)
                        await ctx.send("No more songs left in the queue.")
                        return

        async def playlist_handler():
            # This funtcion hadles the call whenever a playlist is given.

            playlist_id = user_url.split('&list=')[1]
            playlist_request = f"{YOUTUBE_API_URL}playlistItems?part=snippet" \
                               f"&playlistId={playlist_id}&key={YOUTUBE_API_KEY}&maxResults=100"
            playlist_api_response = requests.get(playlist_request)

            if playlist_api_response.status_code != 200:
                await ctx.send(f"Something went wrong. Error code is {playlist_api_response.status_code}")
                return

            data = playlist_api_response.json()
            songs_number = 0

            for item in data['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_title = item['snippet']['title']
                video_data = (video_url, video_title)
                songs_number += 1
                queue_data[guild_id].append(video_data)

            # print(queue_data)

            json.dump(queue_data, open('queue.json', 'w'))
            await ctx.send(f"**{songs_number}** songs have been added to the queue.")
            await queue_loop()

        # Here we use status_check to check if the bot is in a voice channel with the user.
        connect_status = await status_check(ctx, bot_voice)
        if connect_status is False:
            return
        elif connect_status is True:
            await on_play(ctx, user_url)
            return

        if guild_id not in queue_data:
            queue_data[guild_id] = []
            json.dump(queue_data, open('queue.json', 'w'))

        video_info = await YTParser(user_url).parse()

        if video_info is None:
            await ctx.send("No results found. Please try something different.")
            return

        if '&list' in user_url:
            await playlist_handler()
            return

        await music_player(video_info)

    @client.command(aliases=['v', 'vol', 'volume'])
    async def set_volume(ctx, volume: int):
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        if volume > 100:
            await ctx.send("Volume cannot be more than 100.")
            return
        elif volume < 0:
            await ctx.send("Volume cannot be less than 0.")
            return

        bot_voice.source.volume = volume / 100
        await ctx.send(f"Volume set to {volume}%")

    @client.command(aliases=['pause'])
    async def on_pause(ctx):
        # This function will handle the pause for the music player.
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        bot_voice.pause()
        await ctx.send(f"The player has been paused.")

    @client.command(aliases=['r', 'resume'])
    async def on_resume(ctx):
        # This function will resume the player.
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        bot_voice.resume()
        await ctx.send(f"The player has been resumed.")

    @client.command(aliases=['stop'])
    async def on_stop(ctx):
        # This function will stop the player.
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        queue_data = json.load(open('queue.json'))
        queue_data[ctx.guild.id] = []
        json.dump(queue_data, open('queue.json', 'w'))

        bot_voice.stop()
        await ctx.send(f"The player has been stopped.")

    @client.command(aliases=['s', 'skip'])
    async def on_skip(ctx):
        # This function will skip the current song.
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        bot_voice.stop()
        await ctx.send(f"The player has been skipped.")

    @client.command(aliases=['queue'])
    async def on_queue(ctx):
        # This function will show the current queue.
        queue_data = json.load(open('queue.json'))
        guild_id = str(ctx.guild.id)
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        if not queue_data[guild_id]:
            await ctx.send("The queue is empty.")
            return

        titles = []
        item_no = 0
        for item in queue_data[guild_id]:
            item_no += 1
            titles.append(f"({item_no}) {item[1]}")

        titles = ', '.join(titles)
        await ctx.send(f"The current queue is: {titles}")

    @client.command(aliases=['remove'])
    async def on_remove(ctx, song_index: int):
        # This function will remove a song from the queue.

        queue_data = json.load(open('queue.json'))
        guild_id = str(ctx.guild.id)
        song_index -= 1
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        if not queue_data[guild_id]:
            await ctx.send("The queue is empty.")
            return

        if song_index > len(queue_data[guild_id]):
            await ctx.send(f"There are only {len(queue_data[guild_id])} songs in the queue.")
            return

        song_name = queue_data[guild_id][song_index][1]
        queue_data[guild_id].pop(song_index)
        json.dump(queue_data, open('queue.json', 'w'))

        await ctx.send(f"{song_name} has been removed from the queue.")

    on_remove.help = "Removes a song from the queue. Usage: !remove <song number>"

    @client.command(aliases=['disconnect', 'dc', 'dis', 'd'])
    async def on_disconnect(ctx):
        # This function will disconnect the bot from the voice channel.
        bot_voice = ctx.guild.voice_client

        if await status_check(ctx, bot_voice) is False:
            return

        queue_data = json.load(open('queue.json'))
        queue_data[str(ctx.guild.id)] = []
        json.dump(queue_data, open('queue.json', 'w'))

        await bot_voice.disconnect()
        await ctx.send(f"NEØN has been disconnected from the voice channel.")

    client.run(DISCORD_API_KEY)


if __name__ == '__main__':
    main()

""""
    @client.event
    async def on_voice_state_update(member, before, after):
        try:
            voice = after.channel.guild.voice_client
            standby = 0
            while True:
                await asyncio.sleep(5)
                standby += 1
                if voice.is_playing() and not voice.is_paused():
                    standby = 0
                if standby == 40:
                    await voice.disconnect()
                if not voice.is_connected():
                    break
        except AttributeError:
            return

    @client.command(aliases=['help'])
    async def on_help(ctx, args=None):
        help_embed = discord.Embed(title=f"Some help from NEØN!")
        command_names_list = [x.name for x in client.commands]

        # If there are no arguments, just list the commands:
        if not args:
            help_embed.add_field(
                name="List of supported commands:",
                value="\n".join([str(i + 1) + ". " + x.name for i, x in enumerate(client.commands)]),
                inline=False
            )
            help_embed.add_field(
                name="Details",
                value="Type `€help <command name>` for more details about each command.",
                inline=False
            )

        # If the argument is a command, get the help text from that command:
        elif args in command_names_list:
            help_embed.add_field(
                name=args,
                value=client.get_command(args).help
            )

        # If someone is just trolling:
        else:
            help_embed.add_field(
                name="Nope.",
                value="Don't think I got that command, boss!"
            )

        await ctx.send(embed=help_embed)

    # client.add_cog(Player(client))
    client.run(DISCORD_API_KEY)


if __name__ == '__main__':
    main()"""""

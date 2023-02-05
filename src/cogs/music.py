from async_timeout import timeout
from discord.ext import commands
import asyncio
import discord
import functools
import itertools
import random
import youtube_dl

# Silence bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ""


class VoiceError(Exception):
	pass


class YTDLError(Exception):
	pass


class YTDLSource(discord.PCMVolumeTransformer):
	YTDL_OPTIONS = {
	    "format": "bestaudio/best",
	    "extractaudio": True,
	    "audioformat": "mp3",
	    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
	    "restrictfilenames": True,
	    "noplaylist": True,
	    "nocheckcertificate": True,
	    "ignoreerrors": False,
	    "logtostderr": False,
	    "quiet": True,
	    "no_warnings": True,
	    "default_search": "auto",
	    "source_address": "0.0.0.0",
	}

	FFMPEG_OPTIONS = {
	    "before_options":
	    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
	    "options": "-vn",
	}

	ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

	def __init__(self, ctx, source, *, data, volume=0.5):
		super().__init__(source, volume)

		self.requester = ctx.author
		self.channel = ctx.channel
		self.data = data

		self.uploader = data.get("uploader")
		self.uploader_url = data.get("uploader_url")
		date = data.get("upload_date")
		self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
		self.title = data.get("title")
		self.thumbnail = data.get("thumbnail")
		self.description = data.get("description")
		self.duration = self.parse_duration(int(data.get("duration")))
		self.tags = data.get("tags")
		self.url = data.get("webpage_url")
		self.views = data.get("view_count")
		self.likes = data.get("like_count")
		self.dislikes = data.get("dislike_count")
		self.stream_url = data.get("url")

	def __str__(self):
		return f"**{self.title}** by **{self.uploader}**"

	@classmethod
	async def create_source(cls, ctx, search, *, loop=None):
		loop = loop or asyncio.get_event_loop()

		partial = functools.partial(cls.ytdl.extract_info,
		                            search,
		                            download=False,
		                            process=False)
		data = await loop.run_in_executor(None, partial)

		if data is None:
			raise YTDLError(f"Couldn\"t find anything that matches `{search}`")

		if "entries" not in data:
			process_info = data
		else:
			process_info = None
			for entry in data["entries"]:
				if entry:
					process_info = entry
					break

			if process_info is None:
				raise YTDLError(
				    f"Couldn\"t find anything that matches `{search}`")

		webpage_url = process_info["webpage_url"]
		partial = functools.partial(cls.ytdl.extract_info,
		                            webpage_url,
		                            download=False)
		processed_info = await loop.run_in_executor(None, partial)

		if processed_info is None:
			raise YTDLError(f"Couldn\"t fetch `{webpage_url}`")

		if "entries" not in processed_info:
			info = processed_info
		else:
			info = None
			while info is None:
				try:
					info = processed_info["entries"].pop(0)
				except IndexError:
					raise YTDLError(
					    f"Couldn\"t retrieve any matches for `{webpage_url}`")

		return cls(ctx,
		           discord.FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS),
		           data=info)

	@staticmethod
	def parse_duration(duration):
		minutes, seconds = divmod(duration, 60)
		hours, minutes = divmod(minutes, 60)

		duration = f"{str(hours).zfill(2)}:" if hours else ""
		duration += f"{str(minutes).zfill(2)}:"
		duration += f"{str(seconds).zfill(2)}"

		return duration


class Song:

	def __init__(self, source):
		self.source = source
		self.requester = source.requester

	def create_playing_embed(self):
		embed = discord.Embed(title="Playing",
		                      description=f"```\n{self.source.title}\n```",
		                      color=discord.Color.gold())

		embed.add_field(name="Duration", value=self.source.duration)

		embed.add_field(
		    name="Uploader",
		    value=f"[{self.source.uploader}]({self.source.uploader_url})")

		embed.add_field(name="URL", value=f"[Click]({self.source.url})")

		embed.set_thumbnail(url=self.requester.avatar)
		embed.set_image(url=self.source.thumbnail)

		return embed


class SongQueue(asyncio.Queue):

	def __getitem__(self, item):
		if isinstance(item, slice):
			return list(
			    itertools.islice(self._queue, item.start, item.stop,
			                     item.step))
		else:
			return self._queue[item]

	def __iter__(self):
		return self._queue.__iter__()

	def __len__(self):
		return self.qsize()

	def clear(self):
		self._queue.clear()

	def shuffle(self):
		random.shuffle(self._queue)

	def remove(self, index: int):
		del self._queue[index]


class VoiceState:

	def __init__(self, client, ctx):
		self.client = client
		self._ctx = ctx

		self.current = None
		self.voice = None
		self.next = asyncio.Event()
		self.songs = SongQueue()

		self._loop = False
		self._volume = 0.5
		self.skip_votes = set()

		self.audio_player = client.loop.create_task(self.audio_player_task())

	def __del__(self):
		self.audio_player.cancel()

	@property
	def loop(self):
		return self._loop

	@loop.setter
	def loop(self, value):
		self._loop = value

	@property
	def volume(self):
		return self._volume

	@volume.setter
	def volume(self, value):
		self._volume = value

	@property
	def is_playing(self):
		return self.voice and self.current

	async def audio_player_task(self):
		while True:
			self.next.clear()

			if not self.loop:
				# Try to get the next song within 3 minutes.
				# If no song will be added to the queue in time,
				# the player will disconnect.
				try:
					async with timeout(180):
						self.current = await self.songs.get()
				except asyncio.TimeoutError:
					self.client.loop.create_task(self.stop())
					return

			self.current.source.volume = self._volume
			self.voice.play(self.current.source, after=self.play_next_song)
			await self.current.source.channel.send(
			    embed=self.current.create_playing_embed())

			await self.next.wait()

	def play_next_song(self, error=None):
		if error:
			raise VoiceError(str(error))

		self.next.set()

	def skip(self):
		self.skip_votes.clear()

		if self.is_playing:
			self.voice.stop()

	async def stop(self):
		self.songs.clear()

		if self.voice:
			await self.voice.disconnect()
			self.voice = None


class Music(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.voice_states = {}

	def get_voice_state(self, ctx):
		state = self.voice_states.get(ctx.guild.id)
		if not state:
			state = VoiceState(self.client, ctx)
			self.voice_states[ctx.guild.id] = state

		return state

	def cog_unload(self):
		for state in self.voice_states.values():
			self.client.loop.create_task(state.stop())

	def cog_check(self, ctx):
		if not ctx.guild:
			raise commands.NoPrivateMessage(
			    "This command can\"t be used in DM channels.")

		return True

	async def cog_before_invoke(self, ctx):
		ctx.voice_state = self.get_voice_state(ctx)

	async def cog_command_error(self, ctx, error):
		await ctx.send("An error occurred: {}".format(str(error)))

	@commands.command()
	async def join(self, ctx):
		"""Join a voice channel."""

		destination = ctx.author.voice.channel
		if ctx.voice_state.voice:
			await ctx.voice_state.voice.move_to(destination)
			return

		ctx.voice_state.voice = await destination.connect()

	@commands.command()
	async def leave(self, ctx):
		"""Clear the queue and leave the voice channel."""

		if not ctx.voice_state.voice:
			return await ctx.send("Not connected to any voice channel.")

		await ctx.voice_state.stop()
		del self.voice_states[ctx.guild.id]

	@commands.command()
	async def now(self, ctx):
		"""Display the currently playing song."""

		await ctx.send(embed=ctx.voice_state.current.create_playing_embed())

	@commands.command()
	async def pause(self, ctx):
		"""Pause the currently playing song."""

		if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
			ctx.voice_state.voice.pause()

	@commands.command()
	async def resume(self, ctx):
		"""Resume a currently paused song."""

		if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
			ctx.voice_state.voice.resume()

	@commands.command()
	async def stop(self, ctx):
		"""Stop playing song and clear the queue."""

		ctx.voice_state.songs.clear()

		if ctx.voice_state.is_playing:
			ctx.voice_state.voice.stop()

	@commands.command()
	async def skip(self, ctx):
		"""Skip playing song."""

		if not ctx.voice_state.is_playing:
			return await ctx.send("Not playing any music right now...")

		ctx.voice_state.skip()

	@commands.command()
	async def queue(self, ctx):
		"""Show the player"s queue."""

		if len(ctx.voice_state.songs) == 0:
			return await ctx.send("Empty queue.")

		queue = ""
		for i, song in enumerate(ctx.voice_state.songs):
			queue += f"**{i + 1}**: [**{song.source.title}**]({song.source.url})\n"

		embed = (discord.Embed(title="Queue:", description=queue))

		await ctx.send(embed=embed)

	@commands.command()
	async def shuffle(self, ctx):
		"""Shuffle the queue."""

		if len(ctx.voice_state.songs) == 0:
			return await ctx.send("Empty queue.")

		ctx.voice_state.songs.shuffle()

	@commands.command()
	async def remove(self, ctx, index):
		"""Remove a song from the queue at a given index."""

		if len(ctx.voice_state.songs) == 0:
			return await ctx.send("Empty queue.")

		ctx.voice_state.songs.remove(int(index) - 1)

	@commands.command()
	async def loop(self, ctx):
		"""
		Loop the currently playing song.
        Invoking this command again will unloop the song.
        """

		if not ctx.voice_state.is_playing:
			return await ctx.send("Nothing being played at the moment.")

		ctx.voice_state.loop = not ctx.voice_state.loop

	@commands.command()
	async def play(self, ctx, *, search):
		"""Play a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        """

		if not ctx.voice_state.voice:
			await ctx.invoke(self.join)

		async with ctx.typing():
			try:
				source = await YTDLSource.create_source(ctx,
				                                        search,
				                                        loop=self.client.loop)
			except YTDLError as e:
				await ctx.send(
				    f"An error occurred while processing this request: {str(e)}"
				)
			else:
				song = Song(source)

				await ctx.voice_state.songs.put(song)
				await ctx.send(f"Enqueued {str(source)}")


async def setup(client):
	await client.add_cog(Music(client))

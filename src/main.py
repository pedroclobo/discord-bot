import discord
from discord.ext import commands
import os
import asyncio

TOKEN = os.getenv("BOT_TOKEN")

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@client.event
async def on_ready():
	print("useless-roboto is connected to Discord!")


async def load():
	for filename in os.listdir("./src/cogs"):
		if filename.endswith(".py"):
			await client.load_extension("cogs.{}".format(filename[:-3]))


async def main():
	async with client:
		await load()
		await client.start(TOKEN)


asyncio.run(main())

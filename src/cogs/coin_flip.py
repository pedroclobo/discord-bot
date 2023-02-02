from discord.ext import commands
import random


class CoinFlip(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.outcomes = ["Heads", "Tails"]

	@commands.Cog.listener()
	async def on_ready(self):
		print("coin_flip.py is loaded!")

	# Do a coin flip.
	@commands.command()
	async def coin(self, ctx):
		await ctx.channel.send(random.choice(self.outcomes))


async def setup(client):
	await client.add_cog(CoinFlip(client))

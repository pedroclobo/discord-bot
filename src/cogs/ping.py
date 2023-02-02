from discord.ext import commands


class Ping(commands.Cog):

	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print("ping.py is loaded!")

	# Get the bot ping.
	@commands.command()
	async def ping(self, ctx):
		bot_latency = round(self.client.latency * 1000)
		await ctx.channel.send("My latency is {}ms".format(bot_latency))


async def setup(client):
	await client.add_cog(Ping(client))

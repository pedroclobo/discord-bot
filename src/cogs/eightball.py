from discord.ext import commands
import random

ANSWERS = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
    "My reply is no.", "My sources say no.", "Outlook not so good.",
    "Very doubtful."
]


class EightBall(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.answers = ANSWERS

	@commands.Cog.listener()
	async def on_ready(self):
		print("eightball.py is loaded!")

	@commands.command(aliases=["8ball"])
	async def eightball(self, ctx, *, _):
		await ctx.channel.send(random.choice(self.answers))


async def setup(client):
	await client.add_cog(EightBall(client))

from discord.ext import commands
import openai
import os
from guesslang import Guess

openai.api_key = os.getenv("OPEN_AI_TOKEN")


class ChatGpt(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.guess = Guess()

	@commands.Cog.listener()
	async def on_ready(self):
		print("chat_gpt.py is loaded!")

	@commands.command()
	async def ask(self, ctx, *, prompt):
		async with ctx.typing():
			response = openai.Completion.create(
			    engine="text-davinci-003",
			    prompt=prompt,
			    max_tokens=2048,
			    n=1,
			    stop=None,
			    temperature=0.5).choices[0].text

			language = self.guess.language_name(response)

			await ctx.send("```{}\n".format(language) + response + "\n```")


async def setup(client):
	await client.add_cog(ChatGpt(client))

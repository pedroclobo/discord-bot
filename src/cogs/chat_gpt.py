from discord.ext import commands
import openai
import os
from guesslang import Guess

CHUNK_SIZE = 15
PROB_THRESHOLD = 0.5

openai.api_key = os.getenv("OPEN_AI_TOKEN")


class ChatGpt(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.chunk_size = CHUNK_SIZE
		self.guess = Guess()
		self.prob_threshold = PROB_THRESHOLD

	@commands.Cog.listener()
	async def on_ready(self):
		print("chat_gpt.py is loaded!")

	@commands.command()
	async def ask(self, ctx, *, prompt):
		"""Ask anything to ChatGPT."""
		# Place holder for the reply.
		sent_message = await ctx.send("Processing your request...")

		# Get the ChatGPT generator.
		completions = openai.Completion.create(engine="text-davinci-003",
		                                       prompt=prompt,
		                                       max_tokens=2048,
		                                       n=1,
		                                       stop=None,
		                                       temperature=0.5,
		                                       stream=True)

		# Build reply from the stream of chunks
		reply = ""
		for chunk in completions:
			reply += chunk["choices"][0]["text"]
			# Update the message every CHUNK_SIZE chunks to avoid Discord's API rate limit.
			if len(reply) % self.chunk_size == 0:
				await sent_message.edit(content=reply)

		# Programming languages get a code block.
		probabilities = self.guess.probabilities(reply)
		if probabilities[0][1] > self.prob_threshold:
			await sent_message.edit(
			    content="```{}".format(probabilities[0][0]) + reply + "```")
		# Update the message with the last chunk.
		else:
			await sent_message.edit(content=reply)


async def setup(client):
	await client.add_cog(ChatGpt(client))

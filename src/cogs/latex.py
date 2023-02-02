import discord
from discord.ext import commands
import io
import urllib.parse
import urllib.request
from PIL import Image

DPI = 200
MARGIN = 20


class Latex(commands.Cog):

	def __init__(self, client):
		self.client = client
		self.dpi = DPI
		self.margin = MARGIN

	# Request a file from the LaTeX API
	async def generate_file(self, dpi, tex):
		# Build query
		URL = 'https://latex.codecogs.com/gif.latex?{0}'
		TEMPLATE = '\\dpi{{{}}} \\bg_white {}'
		query = TEMPLATE.format(dpi, tex)
		url = URL.format(urllib.parse.quote(query))

		# Make the request
		with urllib.request.urlopen(url) as response:
			bytes = response.read()
		img = Image.open(io.BytesIO(bytes))

		# Create new image with custom margins
		old_size = img.size
		new_size = (old_size[0] + self.margin, old_size[1] + self.margin)
		new_img = Image.new("RGB", new_size, (255, 255, 255))
		new_img.paste(img, (int(self.margin / 2), int(self.margin / 2)))

		# Create a BytesIO object to send the image
		img_bytes = io.BytesIO()
		new_img.save(img_bytes, 'PNG')
		img_bytes.seek(0)

		return img_bytes

	@commands.Cog.listener()
	async def on_ready(self):
		print("latex.py is loaded!")

	@commands.Cog.listener()
	async def on_message(self, message):
		content = message.content
		if content.startswith("$$\n") and content.endswith("\n$$"):
			async with message.channel.typing():
				content = content[3:-3]  # Trim the $$
				file = await self.generate_file(self.dpi, content)
				await message.delete()  # Delete original message
				await message.channel.send(
				    file=discord.File(file, 'latex.png'))


async def setup(client):
	await client.add_cog(Latex(client))

from PyTexturePacker import Packer
from PyTexturePacker.MaxRectsPacker import MaxRectsPacker
from PyTexturePacker import Utils
from PyTexturePacker.PackerInterface.AtlasInterface import AtlasInterface
from PIL import Image
import re, sys, os


class CustomPacker(MaxRectsPacker):
	def pack(self, input_images, output_name, output_path="", input_base_path=None):
		"""
		pack the input images to sheets
		:param input_images: a list of input image paths or a input dir path
		:param output_name: the output file name
		:param output_path: the output file path
		:param input_base_path: the base path of input files
		:return:
		"""

		if isinstance(input_images, (tuple, list)):
			image_rects = Utils.load_images_from_paths(input_images)
		else:
			image_rects = Utils.load_images_from_dir(input_images)

		if self.trim_mode:
			for image_rect in image_rects:
				image_rect.trim(self.trim_mode)

		atlas_list = self._pack(image_rects)

		assert "%d" in output_name or len(atlas_list) == 1, 'more than one output image, but no "%d" in output_name'

		rets = []
		for i, atlas in enumerate(atlas_list):
			texture_file_name = output_name if "%d" not in output_name else output_name % i

			packed_plist = atlas.dump_plist("%s%s" % (texture_file_name, self.texture_format), input_base_path)
			packed_image = atlas.dump_image(self.bg_color)

			rets.append(atlas.image_rect_list)
			assert(len(rets) == i + 1)

			if self.reduce_border_artifacts:
				packed_image = Utils.alpha_bleeding(packed_image)

			Utils.save_plist(packed_plist, os.path.join(output_path, "%s.plist" % texture_file_name))
			Utils.save_image(packed_image, os.path.join(output_path, "%s%s" % (texture_file_name, self.texture_format)))

		return rets


class Sprite:
	def __init__(self, key, name, padding, oy):
		self.name    = name
		self.key     = key
		self.path    = "resources/" + name + ".png"
		self.padding = int(padding) if padding and padding != "" else 0
		self.offset  = int(oy) if oy else 0

		im = Image.open(self.path)
		self.width, self.height = im.size

	def getSpec(self, file, x, y, w, h):
		p = self.padding
		ix, iy = p, p
		iw, ih = w - 2*p, h - 2*p

		if p:
			oy = self.offset
			if oy > 0:
				y += oy
				h -= oy
				iy -= oy
				ih -= oy
			elif oy < 0:
				h += oy
				ih = min(ih, h - iy)

		spec = "\"{}\" Part({}, {}, {}, {})".format(file, x, y, w, h)
		if self.padding is not None:
			spec += " Middle({}, {}, {}, {})".format(ix, iy, iw, ih)

		return spec


def parse(input, output, sheet):
	sheet_no_ext = os.path.splitext(sheet)[0]
	sheet_filename = os.path.basename(sheet)

	sprites = {}
	paths = {}

	content = None
	with open(input) as f:
		content = f.read()

	for filename in re.findall(r"#include \"([A-Za-z0-9_.]+)\"", content):
		with open(filename) as f:
			content = content.replace("#include \"" + filename + "\"", f.read())

	packer = Packer.create(packer_type=CustomPacker, max_width=2048, max_height=2048, bg_color=0x00ffffff, enable_rotated=False)
	for name, padding, ox in re.findall(r"\$\{([A-Za-z0-9_]+)(\:[0-9]+)?(o[+-][0-9]+)?\}", content):
		if sprites.get(name) is not None:
			continue

		try:
			key = "${" + name + padding + ox + "}"
			sprite = Sprite(key, name, padding[1:], ox[1:])
			sprites[key] = sprite
			paths[sprite.path] = True
		except FileNotFoundError:
			print("Sprite not found! " + name)
			sys.exit(1)

	locations = {}
	for image_rect in packer.pack([ p for p in paths.keys() ], sheet_no_ext)[0]:
		locations[image_rect.image_path] = (image_rect.x, image_rect.y, image_rect.width, image_rect.height)

	for sprite in sprites.values():
		loc = locations[sprite.path]
		content = content.replace(sprite.key, sprite.getSpec(sheet_filename, loc[0], loc[1], loc[2], loc[3]))

	with open(output, "w") as f:
		f.write(content)


if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("USAGE: python pack.py path/to/file.source")
		sys.exit(1)

	input = sys.argv[1]
	input_name = os.path.splitext(input)[0]

	if not os.path.isdir("build"):
		os.mkdir("build")

	output = "build/" + input_name + ".style"
	sheet = "build/" + input_name + ".png"
	parse(input, output, sheet)

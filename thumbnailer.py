import os
import sys
from os import listdir
from os.path import isfile, join
from PIL import Image
from pathlib import Path

# python thumbnailer.py 2020/02/01
# for i in {10..25}; do python thumbnailer.py 2020/02/$i; done

size = 350, 350
root = "../www/gallery/upload"

# Arg needs format: 2020/02/01
dir = sys.argv[1]
dir_arr = dir.split('/')
#dir_arr.append("/small")

x = ""
for d in dir_arr:
    x += d + "/"
    print(f"Checking dir: {root}/{x}")
    Path(f"{root}/{x}").mkdir(parents=True, exist_ok=True)

def resize(img_name):
    image = Image.open(f"{root}/{dir}/{img_name}")
    image.thumbnail(size)

    img_file = img_name.split('.')[0]
    img_ext = img_name.split('.')[1]

    if img_name.endswith('jpg'):
        image.save(f"{root}/{dir}/{img_file}_small.{img_ext}", 'JPEG')
    elif img_name.endswith('png'):
        image.save(f"{root}/{dir}/{img_file}_small.{img_ext}", 'PNG')
    else:
        print(f"Skipping: {img_name}")

    print(f"Resized {root}/{dir}/{img_name}")

files = [f for f in listdir(f"{root}/{dir}/") if isfile(join(f"{root}/{dir}/", f))]

for f in files:
    if f != "index.htm":
        resize(f)
        print(f"File name: {f}")


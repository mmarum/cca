import os
import sys
from os import listdir
from os.path import isfile, join
from PIL import Image


"""
When resizing images with PIL, unintended rotation 
often occurs due to EXIF orientation metadata. 
Here's a code example to resize an image while 
preserving its correct orientation:
"""

root = "/Users/matthewmarum/Documents/cca/wheel-wars-2025/img"


dimensions = {}
dimensions["small"] = (400, 400)
dimensions["medium"] = (800, 800)
dimensions["large"] = (1600, 1600)


def resize_image(img_name, size):
    dimension = dimensions[size]
    """
    Resize image while maintaining correct orientation.
    size: tuple (width, height) for maximum dimensions
    """
    try:
        # Open the image
        with Image.open(f"{root}/orig-portrait/{img_name}") as img:
            # Handle EXIF orientation
            try:
                exif = img._getexif()
                if exif:
                    # Common EXIF orientation tags
                    orientation_key = 274  # Orientation
                    if orientation_key in exif:
                        orientation = exif[orientation_key]
                        # Rotate/flip based on orientation
                        if orientation == 3:
                            img = img.rotate(180, expand=True)
                        elif orientation == 6:
                            img = img.rotate(-90, expand=True)
                        elif orientation == 8:
                            img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                # No EXIF data or error, proceed without rotation
                pass

            # Calculate new size maintaining aspect ratio
            img.thumbnail(dimension, Image.Resampling.LANCZOS)

            img_file = img_name.split('.')[0]
            img_ext = img_name.split('.')[1]
            this_img = f"{root}/{size}/{img_file}_{size}-portrait.{img_ext}"

            # Save the image
            img.save(this_img, quality=95)
            print("resized", this_img)
            
    except Exception as e:
        print(f"Error processing image: {e}")


files = [f for f in listdir(f"{root}/orig-portrait/") if isfile(join(f"{root}/orig-portrait/", f))]

size = sys.argv[1]

for img_name in files:
    resize_image(img_name, size)


"""
Key points:
Checks EXIF orientation data and applies necessary rotations
Uses thumbnail() to maintain aspect ratio
Uses LANCZOS resampling for better quality
Includes error handling
Preserves image quality with quality=95
This code prevents unintended rotations by explicitly handling EXIF orientation before resizing. 
Adjust size and quality as needed.
"""

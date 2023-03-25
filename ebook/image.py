# Basically the same as cover.py with some minor differences
import math

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from base64 import b64decode
from math import floor
import textwrap
import requests
import logging

logger = logging.getLogger(__name__)


def make_image(
    message: str,
    width=600,
    height=300,
    fontname="Helvetica",
    font_size=40,
    bg_color=(0, 0, 0),
    textcolor=(255, 255, 255),
    wrap_at=30
):
    """
    This function should only be called if get_image_from_url() fails
    """
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    message = textwrap.fill(message, wrap_at)

    font = _safe_font(fontname, size=font_size)
    message_size = draw.textsize(message, font=font)
    draw_text_outlined(
        draw, ((width - message_size[0]) / 2, 100), message, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    output = BytesIO()
    img.save(output, "JPEG")
    output.name = 'cover.jpeg'
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output


def get_image_from_url(url: str):
    """
    Basically the same as make_cover_from_url()
    """
    try:
        if url.startswith("https://www.filepicker.io/api/"):
            logger.warning("Filepicker.io image detected, converting to Fiction.live image. This might fail.")
            url = f"https://cdn3.fiction.live/fp/{url.split('/')[-1]}?&quality=95"

        logger.info("Downloading image from " + url)

        img = requests.Session().get(url)
        image = BytesIO(img.content)
        image.seek(0)

        image_size = get_size_format(len(image.getvalue()))
        logger.info(f"Image size: {image_size}")

        bigphoto = Image.open(image).convert("RGBA")
        logger.info(f"Image dimensions: {bigphoto.size}")

        if image_size[-2:] == "MB":
            target_pixel_count = 2.8114 * 250_000
            logger.info("Image is MB, compressing with target size of 250KB")
        elif image_size[-2:] == "KB" and int(float(image_size[:-2])) > 200:
            target_pixel_count = 2.8114 * 175_000
            logger.info("Image is greater than 200KB, compressing with target size of 175KB")
        else:
            target_pixel_count = 2.8114 * 100_000
        scale_factor = target_pixel_count / math.prod(bigphoto.size)
        if scale_factor < 1:
            x, y = tuple(int(scale_factor * dim) for dim in bigphoto.size)
            logger.info(f"Resizing image dimensions to ({x}, {y})")
            sml_photo = bigphoto.resize((x, y), resample=Image.LANCZOS)
        else:
            sml_photo = bigphoto

        # Create a new image with a white background
        background_img = Image.new('RGBA', sml_photo.size, "white")
        # Paste the image on top of the background
        background_img.paste(sml_photo, (0, 0), sml_photo)
        sml_photo = background_img.convert('RGB')

        out_io = BytesIO()
        sml_photo.convert("RGB")
        sml_photo.save(out_io, format="JPEG", optimize=True, quality=95)

        logger.info(f"Final image size: {get_size_format(len(out_io.getvalue()))}")
        return out_io.getvalue(), "jpeg", "image/jpeg"

    except Exception as e:
        logger.info("Encountered an error downloading image: " + str(e))
        image = make_image("There was a problem downloading this image.")
        return image.read(), "jpeg", "image/jpeg"


def _convert_to_jpg(image_bytestream):
    png_image = BytesIO()
    Image.open(image_bytestream).save(png_image, format="JPEG")
    png_image.name = 'cover.jpeg'
    png_image.seek(0)

    return png_image
def _convert_to_png(image_bytestream):
    png_image = BytesIO()
    Image.open(image_bytestream).save(png_image, format="PNG")
    png_image.name = 'image.png'
    png_image.seek(0)

    return png_image


def _safe_font(preferred, *args, **kwargs):
    for font in (preferred, "Helvetica", "FreeSans", "Arial"):
        try:
            return ImageFont.truetype(*args, font=font, **kwargs)
        except IOError:
            pass

    # This is pretty terrible, but it'll work regardless of what fonts the
    # system has. Worst issue: can't set the size.
    return ImageFont.load_default()


def draw_text_outlined(draw, xy, text, fill=None, font=None, anchor=None):
    x, y = xy

    # Outline
    draw.text((x - 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x + 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y - 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y + 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)

    # Fill
    draw.text(xy, text=text, fill=fill, font=font, anchor=anchor)


def get_image_size(data):
    img = Image.open(BytesIO(data))
    owidth, oheight = img.size
    return owidth, oheight


imagetypes = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
}


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


convtype = {'jpg': 'JPEG', 'png': 'PNG'}


def normalize_format_name(fmt):
    if fmt:
        fmt = fmt.lower()
        if fmt == 'jpeg':
            fmt = 'jpg'
    return fmt


if __name__ == '__main__':
    f = make_image(
        'Test of a Title which is quite long and will require multiple lines')
    with open('output.png', 'wb') as out:
        out.write(f.read())

# Basically the same as cover.py with some minor differences
import math

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from base64 import b64decode
from math import floor
import textwrap
import requests
import logging
import os
import sys

logger = logging.getLogger(__name__)


def convert_image(url, sizes=(580, 725), grayscale=False,
                  removetrans=True, imgtype="jpg", background='#ffffff', jpg_quality=95):
    # logger.debug("Pillow convert_image called")
    export = False
    logger.info("Downloading image from " + url)
    data = requests.Session().get(url).content
    img = Image.open(BytesIO(data))

    owidth, oheight = img.size
    nwidth, nheight = sizes
    scaled, nwidth, nheight = fit_image(owidth, oheight, nwidth, nheight)
    if scaled:
        img = img.resize((nwidth, nheight), Image.ANTIALIAS)
        export = True

    if normalize_format_name(img.format) != imgtype:
        if img.mode == "P":
            # convert pallete gifs to RGB so jpg save doesn't fail.
            img = img.convert("RGB")
        export = True

    if removetrans and img.mode == "RGBA":
        background = Image.new('RGBA', img.size, background)
        # Paste the image on top of the background
        background.paste(img, img)
        img = background.convert('RGB')
        export = True

    if grayscale and img.mode != "L":
        img = img.convert("L")
        export = True

    if export:
        outsio = BytesIO()
        if imgtype == 'jpg':
            img.save(outsio, convtype[imgtype], quality=jpg_quality, optimize=True)
        else:
            img.save(outsio, convtype[imgtype])
        return outsio.getvalue(), imgtype, imagetypes[imgtype]
    else:
        # logger.debug("image used unchanged")
        return data, imgtype, imagetypes[imgtype]


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
        logger.info("Downloading image from " + url)
        img = requests.Session().get(url)
        image = BytesIO(img.content)
        image.seek(0)

        img_format = Image.open(image).format

        bigphoto = Image.open(image).convert("RGBA")
        # Establish Target Size
        target_byte_count = 95_000
        target_pixel_count = 2.8114 * target_byte_count
        # Note that an image which measures
        #     1920 by 1080
        # pixels is approximately
        #      737,581 bytes
        # So we have
        #     2.8114 pixels per byte
        scale_factor = target_pixel_count / math.prod(bigphoto.size)
        # if
        #     the image is already smaller than the target size
        # then
        #     Do not enlarge the image.
        #     keep the image the same size.
        # scale_factor = 1 if scale_factor >= 1 else scale_factor
        if scale_factor < 1:
            # set new photographs size
            # `bigphoto.size` is something like (20000, 37400)
            sml_size = tuple(int(scale_factor * dim) for dim in bigphoto.size)
            # We cannot have two-and-a-half pixels
            # convert decimal numbers into whole numbers
            # sml_size = (int(number) for number in sml_size_list)
            # cast `sml_size` to the same data-type as `bigphoto.size`
            # copy_constructor = type(bigphoto.size)
            # new_sml_size = copy_constructor(sml_size)
            # create new photograph
            sml_photo = bigphoto.resize(sml_size, resample=Image.LANCZOS)
        else:
            sml_photo = bigphoto

        background_img = Image.new('RGBA', sml_photo.size, (0, 0, 0, 0))
        # # Paste the image on top of the background
        background_img.paste(sml_photo, (0, 0), sml_photo)
        sml_photo = background_img

        out_io = BytesIO()
        sml_photo.save(out_io, format="GIF", optimize=True, quality=95)
        logger.info("Image size after compression: " + str(get_size_format(len(out_io.getvalue()))))
        return out_io.getvalue(), "GIF", "image/gif"

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


def fit_image(width, height, pwidth, pheight):
    '''
    Fit image in box of width pwidth and height pheight.
    @param width: Width of image
    @param height: Height of image
    @param pwidth: Width of box
    @param pheight: Height of box
    @return: scaled, new_width, new_height. scaled is True iff new_width and/or new_height is different from width or height.
    '''
    scaled = height > pheight or width > pwidth
    if height > pheight:
        corrf = pheight / float(height)
        width, height = floor(corrf * width), pheight
    if width > pwidth:
        corrf = pwidth / float(width)
        width, height = pwidth, floor(corrf * height)
    if height > pheight:
        corrf = pheight / float(height)
        width, height = floor(corrf * width), pheight

    return scaled, int(width), int(height)


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


def download_from_url_and_convert_image(
    url: str,
    # sizes=(580, 725),
    grayscale=False,
    remove_trans=False,
    img_ext_type="jpg",
    background='#ffffff',
    image_quality=85
) -> bytes:
    """
    Stole this from FanFicFare
    """
    logger.debug("Pillow convert_image called")
    try:
        logger.info("Downloading image from " + url)
        url = url.strip()

        if url.startswith("data:image") and 'base64' in url:
            head, base64data = url.split(',', 1)
            file_ext = head.split(';')[0].split('/')[1]
            imgdata = b64decode(base64data)
            image_bytes = BytesIO(imgdata).read()
            if file_ext.lower() not in ["jpg", "jpeg"]:
                return _convert_to_jpg(image_bytes).read()
            return image_bytes
        else:
            image_response = requests.Session().get(url)
            image_bytes = BytesIO(image_response.content)

        export = False
        img = Image.open(image_bytes)
        logger.info("Image size: " + str(get_size_format(len(image_bytes.getvalue()))))
        o_width, o_height = img.size
        # n_width, n_height = sizes
        # scaled, n_width, n_height = fit_image(o_width, o_height, n_width, n_height)

        # if scaled:
        # img = img.resize((n_width, n_height), Image.ANTIALIAS)
        # export = True

        if normalize_format_name(img.format) != img_ext_type:
            if img.mode == "P":
                # convert pallet gifs to RGB so jpg save doesn't fail.
                img = img.convert("RGB")
            export = True

        if remove_trans and img.mode == "RGBA":
            background_img = Image.new('RGBA', img.size, background)
            # Paste the image on top of the background
            background_img.paste(img)
            img = background_img.convert('RGB')
            export = True

        if export:
            out_io = BytesIO()
            img = img.convert("RGB")
            if img_ext_type == 'jpg':
                img.save(out_io, convtype[img_ext_type], quality=image_quality, optimize=True)
            else:
                img.save(out_io, "JPEG")
            logger.info("Image size after compression: " + str(get_size_format(len(image_bytes.getvalue()))))
            return out_io.getvalue()

    except Exception as e:
        logger.info("Encountered an error downloading image: " + str(e))
        # image = make_image("There was a problem downloading this image.")
        # return image.read()


if __name__ == '__main__':
    f = make_image(
        'Test of a Title which is quite long and will require multiple lines')
    with open('output.png', 'wb') as out:
        out.write(f.read())

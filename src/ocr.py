import logging

import pytesseract
from PIL import ImageFile, Image

# TODO: Remove type annotations through comments?


def filter_image(image: ImageFile.ImageFile) -> Image.Image:
    # Return only the upper-left portion of the image in black-and-white
    w, h = image.size
    # Take the upper-left portion of the screen
    im = image.crop(0, 0, w // 2, h // 2) # type: Image.Image
    # Return the cropped image in black and white
    return im.convert('1')


def check_if_string_in_image(string: str, image: ImageFile.ImageFile) -> bool:
    if string == "":
        # Let's just assume that if this is passed that this is probably a bug.
        # Probably.
        return False
    im = filter_image(image)
    ocr_output = str(pytesseract.image_to_string(im))
    logging.debug("OCR Output: %s", ocr_output)
    return string in ocr_output

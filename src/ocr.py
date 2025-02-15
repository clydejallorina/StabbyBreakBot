import pytesseract
from PIL import ImageFile

def check_if_string_in_image(string: str, image: ImageFile.ImageFile) -> bool:
    if string == "":
        # Let's just assume that if this is passed that this is probably a bug.
        # Probably.
        return False
    ocr_output = str(pytesseract.image_to_string(image))
    return string in ocr_output

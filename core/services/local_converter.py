import os
import cv2
from django.conf import settings


def converter(
    filename: str,
    image_path: str,
    detail_level: int = 21,
) -> str:
    base_filename = os.path.basename(filename)
    name_no_ext = os.path.splitext(base_filename)[0]
    sketch_filename = name_no_ext + "_sketch.jpg"

    converted_dir = os.path.join(settings.MEDIA_ROOT, "temp")
    if not os.path.exists(converted_dir):
        os.makedirs(converted_dir)

    sketch_path = os.path.join(converted_dir, sketch_filename)
    # Resto do processamento
    original_image = cv2.imread(image_path)
    gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    inverted_image = 255 - gray_image

    if detail_level < 1:
        detail_level = 1
    if detail_level % 2 == 0:
        detail_level += 1

    blurred_image = cv2.GaussianBlur(inverted_image, (detail_level, detail_level), 0)
    inverted_blurred_image = 255 - blurred_image
    sketch = cv2.divide(gray_image, inverted_blurred_image, scale=256.0)

    cv2.imwrite(sketch_path, sketch)
    return sketch_path

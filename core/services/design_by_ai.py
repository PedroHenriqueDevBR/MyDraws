import os

from typing import Optional
from io import BytesIO
from PIL import Image
from decouple import config

from django.conf import settings
from google import genai
from google.genai import types


class DesignByAI:
    def __init__(
        self,
        image_path: str,
        model_name="gemini-2.0-flash-preview-image-generation",
        prompt: Optional[str] = None,
    ):
        self.image_filename = image_path.split("/")[-1]
        self.image = Image.open(image_path)
        self.client = genai.Client(api_key=config("GENAI_API_KEY"))  # type: ignore
        self.model = model_name
        # self.text_input = (
        #     "Convert this image into a black and white line drawing"
        #     "in coloring book style. Preserve the key shapes and "
        #     "features of the original image — whether it's a person, "
        #     "object, animal, or landscape — using only clean and "
        #     "sharp outlines, with no shading or color fill. The "
        #     "result should clearly reflect the identity and "
        #     "structure of the image's main elements, in a simple "
        #     "style suitable for printing and hand coloring with "
        #     "pencils or markers. Keep the background blank or "
        #     "minimally outlined to emphasize the main subjects."
        # )
        self.text_input = (
            "Image-to-image conversion. Output a clean BLACK-ON-WHITE LINE ART drawing "
            "in the style of the 'coloring page': simple geometric forms, "
            "smooth outlines, minimal details, big expressive eyes, small simple nose and mouth, "
            "flat shapes, and playful proportions. "
            "PRESERVE: the subject’s identity (face shape and key features), hairstyle, pose, clothing, "
            "camera angle, and overall composition from the input photo. if the subject is a person using glasses dont draw your eyes over the glasses"
            "BACKGROUND: keep the same layout but simplify to the coloring page aesthetic "
            "(flat, minimal shapes; no added or removed objects). "
            "LINES: bold, smooth, closed contours suitable for a coloring book; consistent weight for outer contours, "
            "slightly lighter interiors. "
            "RESTRICTIONS: black lines on white only—no grayscale, shading, crosshatching, textures, gradients, or color. "
            "Do not invent new characters, change the subject’s age, expression, or outfit, or alter the scene."
        )

        if prompt is not None:
            self.text_input = prompt

    def minify_image_size(self, img: Image.Image) -> Image.Image:
        img_format = img.format or "JPEG"

        if img_format.upper() == "JPEG" and img.mode != "RGB":
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format=img_format, optimize=True, quality=70)
        buffer.seek(0)
        return Image.open(buffer)

    def generate_from_gemini(self) -> tuple[str, Image.Image]:
        minified_image = self.minify_image_size(self.image)
        response = self.client.models.generate_content(
            model=self.model,
            contents=[self.text_input, minified_image],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        base_filename = os.path.basename(self.image_filename)
        name_no_ext = os.path.splitext(base_filename)[0]
        ia_filename = name_no_ext + "_ia.jpg"

        converted_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        if not os.path.exists(converted_dir):
            os.makedirs(converted_dir)

        ia_path = os.path.join(converted_dir, ia_filename)

        for part in response.candidates[0].content.parts:  # type: ignore
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(
                    BytesIO((part.inline_data.data)),  # type: ignore
                )
                image.save(ia_path)

        return ia_path, image

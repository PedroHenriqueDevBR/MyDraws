import os
import base64
from typing import Optional
from io import BytesIO
from PIL import Image
from openai import OpenAI
from django.conf import settings
from decouple import config


class DesignByOpenAI:
    def __init__(
        self,
        image_path: str,
        model_name: str = "gpt-image-1",
        prompt: Optional[str] = None,
    ):
        self.image_filename = os.path.basename(image_path)
        self.image_path = image_path
        self.image = Image.open(image_path)
        self.client = OpenAI(
            api_key=config("OPENAI_API_KEY"),  # type: ignore
            organization=config("OPENAI_ORG_ID"),  # type: ignore
        )  # type ignore
        self.model = model_name

        # Prompt padrão
        self.prompt = (
            "Transform the image into an anime scene, sunset in the background"
        )

        if prompt:
            self.prompt = prompt

    def minify_image_size(self, img: Image.Image) -> BytesIO:
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", optimize=True, quality=70)
        buffer.seek(0)
        buffer.name = "image.jpg"
        return buffer

    def generate(self) -> str:
        # Reduz o tamanho para melhorar performance e atender requisitos de API
        image_buffer = self.minify_image_size(self.image)
        # return self.image_path

        result = self.client.images.edit(
            model=self.model,
            image=[image_buffer],
            prompt=self.prompt,
            n=1,
            output_format="jpeg",
            # response_format="b64_json",
            quality="low",
            input_fidelity="low",
            size="1024x1536",
        )

        image_base64 = result.data[0].b64_json  # type: ignore
        image_bytes = base64.b64decode(image_base64)  # type: ignore
        converted_image = Image.open(BytesIO(image_bytes))

        # Caminho onde salvar a imagem
        name_no_ext = os.path.splitext(self.image_filename)[0]
        ia_filename = name_no_ext + "_ia.jpg"
        converted_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        os.makedirs(converted_dir, exist_ok=True)
        ia_path = os.path.join(converted_dir, ia_filename)

        converted_image.save(ia_path, "JPEG")

        return ia_path

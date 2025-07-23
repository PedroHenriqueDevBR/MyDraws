import os
from io import BytesIO
from PIL import Image
from decouple import config
import subprocess

from django.conf import settings
from google import genai
from google.genai import types


class DesignByAI:
    def __init__(
        self,
        image_path: str,
        model_name="gemini-2.0-flash-preview-image-generation",
    ):
        self.image_filename = image_path.split("/")[-1]
        self.image = Image.open(image_path)
        self.client = genai.Client(api_key=config("GENAI_API_KEY"))  # type: ignore
        self.text_input = (
            "Convert this image into a black and white line drawing" 
            "in coloring book style. Preserve the key shapes and "
            "features of the original image — whether it's a person, "
            "object, animal, or landscape — using only clean and "
            "sharp outlines, with no shading or color fill. The "
            "result should clearly reflect the identity and "
            "structure of the image's main elements, in a simple "
            "style suitable for printing and hand coloring with "
            "pencils or markers. Keep the background blank or "
            "minimally outlined to emphasize the main subjects."
        )
        # self.text_input = (
        #     "Convert this image into a black and white line drawing"
        #     "in coloring book style. — whether it's a person, "
        #     "object, animal, or landscape — using only clean and "
        #     "sharp outlines, with no shading or color fill. The "
        #     "result should cartoonishly reflect the identity and "
        #     "structure of the image's main elements, in a simple "
        #     "style suitable for printing and hand coloring with "
        #     "pencils or markers. Design the background to be minimalistic too."
        # )
        self.model = model_name

    def generate_from_model(
        self,
        image_model: str = "imagen-3.0-capability-001",
    ) -> list[tuple[str, Image.Image]] | None:
        """
        imagen-3.0-capability-001
        models/imagen-3.0-generate-002
        models/imagen-4.0-generate-preview-06-06
        """

        token = (
            subprocess.check_output("gcloud auth print-access-token", shell=True)
            .decode()
            .strip()
        )
        project = (
            subprocess.check_output(
                "gcloud config list --format='value(core.project)'", shell=True
            )
            .decode()
            .strip()
        )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-User-Project": project,
            "Authorization": f"Bearer {token}",
        }

        response = self.client.models.edit_image(
            model=image_model,
            prompt=self.text_input,
            reference_images=[
                types.RawReferenceImageOrDict(  # type: ignore
                    reference_image=self.image,
                    reference_id=1,
                )
            ],
            config=types.EditImageConfigOrDict(  # type: ignore
                number_of_images=1,
                output_mime_type="image/jpeg",
                person_generation="ALLOW_ADULT",
                http_options=types.HttpOptionsOrDict(  # type: ignore
                    headers=headers,
                ),
            ),
        )

        if not response.generated_images:
            print("No images generated.")
            return

        base_filename = os.path.basename(self.image_filename)
        name_no_ext = os.path.splitext(base_filename)[0]

        converted_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        if not os.path.exists(converted_dir):
            os.makedirs(converted_dir)

        if len(response.generated_images) != 1:
            print("Number of images generated does not match the requested number.")

        result = []

        for index, generated_image in enumerate(response.generated_images):
            ia_filename = name_no_ext + f"_ia_{index}.jpg"
            ia_path = os.path.join(converted_dir, ia_filename)
            image = Image.open(
                BytesIO(generated_image.image.image_bytes),  # type: ignore
            )
            image.save(ia_path)
            result.append((ia_path, image))

        return result

    def generate_from_gemini(self) -> tuple[str, Image.Image]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=[self.text_input, self.image],
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

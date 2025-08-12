import os
from pathlib import Path

from celery import shared_task
from django.core.files import File

from core.models import UploadedImage
from core.services.design_by_openai import DesignByOpenAI
from core.utils import use_credit_amount


@shared_task
def generate_ai_image_task(uploaded_image_id: int):
    uploaded_image = UploadedImage.objects.get(id=uploaded_image_id)
    profile = uploaded_image.profile
    designer = DesignByOpenAI(image_path=uploaded_image.image.path)
    converted_image_path = designer.generate()

    print(f"Converted image path: {converted_image_path}")  # Debugging line

    if not converted_image_path:
        return

    filename = os.path.basename(converted_image_path)
    with open(converted_image_path, "rb") as file:
        django_file = File(file, name=filename)
        UploadedImage.objects.create(
            title=f"Converted - {uploaded_image.title}",
            image=django_file,
            profile=profile,
            based_on=uploaded_image,
        )

    use_credit_amount(profile, 3, "AI_GENERATION")  # type: ignore
    return converted_image_path

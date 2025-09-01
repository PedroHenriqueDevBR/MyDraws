from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.shortcuts import redirect

from core.models import UploadedImage
from core.services import local_converter
from core.tasks import generate_ai_image_task
from core.types import CustomRequest
from core.utils import use_credit_amount


@login_required
def simple_convert(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have enough credits to perform this action, please buy some credits.",
        )
        return redirect("show_uploaded_image", image_id=image_id)

    detail_level = int(request.POST.get("detail_level", 21))
    converted_image_path = local_converter.converter(
        filename=uploaded_image.image.name,
        image_path=uploaded_image.image.path,
        detail_level=detail_level,
    )

    converted_image_file = File(open(converted_image_path, "rb"))

    UploadedImage.objects.create(
        title=f"Converted {uploaded_image.title}",
        image=converted_image_file,
        profile=request.user,
        based_on=uploaded_image,
    )

    Path(converted_image_path).unlink()

    messages.add_message(
        request,
        messages.SUCCESS,
        "Art converted successfully! 🎨✨ You can see the new image below.",
    )

    use_credit_amount(user, 1)  # type: ignore

    return redirect(
        "show_uploaded_image",
        image_id=uploaded_image.id,  # type: ignore
    )


@login_required
def generate_by_ai(request: CustomRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image or uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have enough credits to perform this action, please buy some credits.",
        )
        return redirect("show_uploaded_image", image_id=image_id)

    # Celery task
    task = generate_ai_image_task.delay(uploaded_image.id)  # type: ignore
    request.session[f"ai_task_{image_id}"] = task.id

    messages.add_message(
        request,
        messages.INFO,
        "AI art generation has been started! You will be notified when it's ready.",
    )

    return redirect("show_uploaded_image", image_id=uploaded_image.id)  # type: ignore

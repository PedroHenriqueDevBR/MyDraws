from django.shortcuts import render, redirect
from django.http.request import HttpRequest

from .forms import ImageUploadForm
from .models import UploadedImage
from .services import local_converter
from django.core.files import File
from pathlib import Path


def home(request: HttpRequest):
    if not request.user.is_authenticated:
        return render(
            request,
            "error.html",
            {"message": "You must be logged in to view this page."},
        )

    uploaded_images = UploadedImage.objects.filter(profile=request.user.profile, based_on__isnull=True).order_by("-created_at")
    return render(request, "home.html", {"uploaded_images": uploaded_images})


def upload_image(request: HttpRequest):
    if not request.user.is_authenticated:
        return render(
            request,
            "error.html",
            {"message": "You must be logged in to view this page."},
        )

    if request.method == "POST":
        image_file = request.FILES["image"]
        uploaded_image = UploadedImage.objects.create(
            title=request.POST.get("title", "Untitled"),
            image=image_file,
            profile=request.user.profile,
        )

        return redirect("show_uploaded_image", image_id=uploaded_image.id)
    else:
        form = ImageUploadForm()
    return render(request, "upload.html", {"form": form})


def show_uploaded_image(request: HttpRequest, image_id: int):
    if not request.user.is_authenticated:
        return render(
            request,
            "error.html",
            {"message": "You must be logged in to view this page."},
        )

    uploaded_image = UploadedImage.objects.filter(id=image_id).first()
    if not uploaded_image:
        return render(
            request,
            "error.html",
            {"message": "Image not found."},
        )

    return render(request, "show_image.html", {"uploaded_image": uploaded_image})


def simple_convert(request: HttpRequest, image_id: int):
    if not request.user.is_authenticated:
        return render(
            request,
            "error.html",
            {"message": "You must be logged in to perform this action."},
        )

    uploaded_image = UploadedImage.objects.filter(id=image_id).first()
    if not uploaded_image:
        return render(
            request,
            "error.html",
            {"message": "Image not found."},
        )

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
        profile=request.user.profile,
        based_on=uploaded_image,
    )
    
    Path(converted_image_path).unlink()

    return redirect("show_uploaded_image", image_id=uploaded_image.id)

from pathlib import Path

from django.core.files import File
from django.http.request import HttpRequest
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages

from core.services.design_by_ai import DesignByAI

from .forms import ImageUploadForm
from .models import UploadedImage, Book
from .services import local_converter


def custom_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    return redirect("login")


@login_required
def home(request: HttpRequest):
    books = Book.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "core/home.html", {"books": books})


@login_required
def book_detail(request: HttpRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to view this book.",
        )
        return redirect("home")

    uploaded_images = book.uploaded_images.all().order_by("-created_at")
    return render(
        request,
        "core/book_detail.html",
        {"book": book, "uploaded_images": uploaded_images},
    )


@login_required
def book_create(request: HttpRequest):
    if request.method == "POST":
        title = request.POST.get("title", "Untitled Book")
        description = request.POST.get("description", "")
        book = Book.objects.create(
            title=title,
            description=description,
            author=request.user,
        )
        return redirect("book_detail", book_id=book.id)
    else:
        return redirect("home")


@login_required
def upload_image(request: HttpRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to view this book.",
        )
        return redirect("home")

    if request.method == "POST":
        image_file = request.FILES["image"]
        uploaded_image = UploadedImage.objects.create(
            title=request.POST.get("title", "Untitled"),
            image=image_file,
            profile=request.user,
            book=book,
        )

        return redirect("show_uploaded_image", image_id=uploaded_image.id)
    else:
        form = ImageUploadForm()
    return render(request, "core/upload.html", {"form": form})


@login_required
def show_uploaded_image(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    return render(request, "core/show_image.html", {"uploaded_image": uploaded_image})


@login_required
def simple_convert(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have enough credits to perform this action. Please purchase more credits.",
        )
        return redirect("home")

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

    return redirect("show_uploaded_image", image_id=uploaded_image.id)


@login_required
def generate_by_ai(request: HttpRequest, image_id: int):
    user = request.user
    uploaded_image = UploadedImage.objects.filter(id=image_id).first()

    if not uploaded_image:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    if uploaded_image and uploaded_image.profile != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have permission to convert this image.",
        )
        return redirect("home")

    if not user.credit_amount or user.credit_amount <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "You do not have enough credits to perform this action. Please purchase more credits.",
        )
        return redirect("home")

    designer = DesignByAI(image_path=uploaded_image.image.path)
    converted_image_path, _ = designer.generate_from_gemini()
    converted_image_file = File(open(converted_image_path, "rb"))

    UploadedImage.objects.create(
        title=f"IA {uploaded_image.title}",
        image=converted_image_file,
        profile=request.user,
        based_on=uploaded_image,
    )

    Path(converted_image_path).unlink()

    return redirect("show_uploaded_image", image_id=uploaded_image.id)

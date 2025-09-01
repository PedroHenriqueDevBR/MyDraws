from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from core.forms import ImageUploadForm
from core.models import Book, UploadedImage
from core.types import CustomRequest


@login_required
def home(request: CustomRequest):
    books = Book.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "core/home.html", {"books": books})


@login_required
def book_detail(request: CustomRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    uploaded_images = book.uploaded_images.all().order_by("-id")  # type: ignore
    return render(
        request,
        "core/book_detail.html",
        {"book": book, "uploaded_images": uploaded_images},
    )


@login_required
def book_create(request: CustomRequest):
    if request.method == "POST":
        title = request.POST.get("title", "Untitled Book")
        description = request.POST.get("description", "")
        book = Book.objects.create(
            title=title,
            description=description,
            author=request.user,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Book '{book.title}' created successfully.",
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "You can start adding pages to this book.",
        )
        return redirect("book_detail", book_id=book.id)  # type: ignore
    else:
        return redirect("home")


@login_required
def upload_image(request: CustomRequest, book_id: int):
    user = request.user
    book = Book.objects.filter(id=book_id, author=request.user).first()

    if not book:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
        )
        return redirect("home")

    if book.author != user:
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have permission to view this book.",
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
        messages.add_message(
            request,
            messages.SUCCESS,
            "Magic page uploaded successfully, time for fun! 🎉",
        )
        return redirect("show_uploaded_image", image_id=uploaded_image.id)  # type: ignore
    else:
        form = ImageUploadForm()
    return render(request, "core/upload.html", {"form": form})


@login_required
def show_uploaded_image(request: CustomRequest, image_id: int):
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

    has_imagem_task = request.session.get(f"ai_task_{image_id}") is not None

    return render(
        request,
        "core/show_image.html",
        {
            "uploaded_image": uploaded_image,
            "has_imagem_task": has_imagem_task,
        },
    )


@login_required
def remove_uploaded_image(request: CustomRequest, image_id: int):
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

    based_on = uploaded_image.based_on
    if based_on:
        book_id = based_on.book.id  # type: ignore
    else:
        book_id = uploaded_image.book.id  # type: ignore
    uploaded_image.delete()

    if based_on is not None:
        redirect_url = reverse("show_uploaded_image", kwargs={"image_id": based_on.id})
        return redirect(redirect_url)

    redirect_url = reverse("book_detail", kwargs={"book_id": book_id})
    return redirect(redirect_url)

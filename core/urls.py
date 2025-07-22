from django.urls import path
from core import views

urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "upload/<int:book_id>/",
        views.upload_image,
        name="upload_image",
    ),
    path(
        "book/create/",
        views.book_create,
        name="book_create",
    ),
    path(
        "book/<int:book_id>/",
        views.book_detail,
        name="book_detail",
    ),
    path(
        "image/<int:image_id>/",
        views.show_uploaded_image,
        name="show_uploaded_image",
    ),
    path(
        "image/<int:image_id>/simple_convert/",
        views.simple_convert,
        name="simple_convert",
    ),
    path(
        "image/<int:image_id>/generate_by_ai/",
        views.generate_by_ai,
        name="generate_by_ai",
    ),
    path(
        "route/webhook/",
        views.webhook,
        name="webhook",
    ),
]

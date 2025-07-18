from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_image, name='upload_image'),
    path('image/<int:image_id>/', views.show_uploaded_image, name='show_uploaded_image'),
    path('image/<int:image_id>/simple_convert/', views.simple_convert, name='simple_convert'),
]

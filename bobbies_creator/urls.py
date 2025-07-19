from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import custom_logout
from core import urls as core_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(core_urls)),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html"),
        name="login",
    ),
    path("logout/", custom_logout, name="custom_logout"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.http import HttpRequest
from core.models import Profile


# This request override the AbstractUser to Profile
class CustomRequest(HttpRequest):
    user: Profile

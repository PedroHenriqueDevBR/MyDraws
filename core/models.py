from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    credit_amount = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_premium = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    def __str__(self) -> str:
        if not self.user:
            return "Anonymous Profile"

        if self.user.first_name:
            return f"{self.user.get_full_name()}"

        return f"{self.user.username}"


class CreditTransaction(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.transaction_type.capitalize()} of {self.amount} credits for {self.profile.user.username}"


def upload_to(instance, filename):
    if not instance.profile or not instance.profile.user:
        return f"uploads/{filename}"
    return f"uploads/{instance.profile.user.username}/{filename}"


class UploadedImage(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to=upload_to)
    created_at = models.DateTimeField(auto_now_add=True)
    based_on = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="variations",
        null=True,
        blank=True,
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="uploaded_images",
    )

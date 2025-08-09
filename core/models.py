from django.db import models
from django.contrib.auth.models import AbstractUser


class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3)

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name_plural = "Countries"


class State(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3)
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        related_name="states",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name_plural = "States"


class City(models.Model):
    name = models.CharField(max_length=100)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        related_name="cities",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name_plural = "Cities"


class Address(models.Model):
    house_number = models.CharField(max_length=50, null=True, blank=True)
    street = models.CharField(max_length=255)
    neighborhood = models.CharField(max_length=100, blank=True, null=True)
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        related_name="addresses",
        null=True,
        blank=True,
    )
    postal_code = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.street}, {self.neighborhood or ''}, {self.city or 'No City'}, {self.postal_code or 'No Postal Code'}"

    class Meta:
        verbose_name_plural = "Addresses"


class Profile(AbstractUser):
    credit_amount = models.IntegerField(default=0)
    is_premium = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        related_name="profiles",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        if self.first_name:
            return f"{self.get_full_name()}"

        return f"{self.username}"

    class Meta:
        verbose_name_plural = "Profiles"


class ProfileAddress(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        related_name="addresses",
        null=True,
        blank=True,
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        related_name="profile_addresses",
        null=True,
        blank=True,
    )
    default = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.profile or 'No Profile'} - {self.address or 'No Address'}"

    class Meta:
        verbose_name_plural = "Profile Addresses"


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
        return f"{self.transaction_type} of {self.amount} credits for {self.profile}"

    class Meta:
        verbose_name_plural = "Credit Transactions"


class Book(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="books",
    )

    def __str__(self) -> str:
        return f'{self.title} by {self.author or "No Author"}'

    class Meta:
        verbose_name_plural = "Books"


def upload_to(instance, filename):
    return f"uploads/{filename}"


class UploadedImage(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to=upload_to)
    created_at = models.DateTimeField(auto_now_add=True)
    default = models.BooleanField(default=False)
    based_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="variations",
        null=True,
        blank=True,
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        related_name="uploaded_images",
        null=True,
        blank=True,
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        related_name="uploaded_images",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.title}"

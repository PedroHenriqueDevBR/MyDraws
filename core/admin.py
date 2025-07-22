from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from core.models import (
    Country,
    State,
    City,
    Address,
    Profile,
    ProfileAddress,
    CreditTransaction,
    Book,
    UploadedImage,
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "states_count")
    list_filter = ("code",)
    search_fields = ("name", "code")
    ordering = ("name",)

    def states_count(self, obj):
        return obj.states.count()

    states_count.short_description = "Estados"


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country", "cities_count")
    list_filter = ("country",)
    search_fields = ("name", "code", "country__name")
    ordering = ("country__name", "name")
    autocomplete_fields = ("country",)

    def cities_count(self, obj):
        return obj.cities.count()

    cities_count.short_description = "Cidades"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "country_name", "addresses_count")
    list_filter = ("state__country", "state")
    search_fields = ("name", "state__name", "state__country__name")
    ordering = ("state__country__name", "state__name", "name")
    autocomplete_fields = ("state",)

    def country_name(self, obj):
        return obj.state.country.name if obj.state and obj.state.country else "-"

    country_name.short_description = "País"

    def addresses_count(self, obj):
        return obj.addresses.count()

    addresses_count.short_description = "Endereços"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_address", "city", "postal_code", "profiles_count")
    list_filter = ("city__state__country", "city__state", "city")
    search_fields = ("street", "neighborhood", "city__name", "postal_code")
    ordering = (
        "city__state__country__name",
        "city__state__name",
        "city__name",
        "street",
    )
    autocomplete_fields = ("city",)

    def full_address(self, obj):
        parts = []
        if obj.house_number:
            parts.append(obj.house_number)
        parts.append(obj.street)
        if obj.neighborhood:
            parts.append(obj.neighborhood)
        return ", ".join(parts)

    full_address.short_description = "Endereço"

    def profiles_count(self, obj):
        return obj.profile_addresses.count()

    profiles_count.short_description = "Perfis"


@admin.register(Profile)
class ProfileAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "get_full_name",
        "credit_amount",
        "is_premium",
        "is_verified",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "is_premium",
        "is_verified",
        "is_active",
        "is_staff",
        "country",
        "date_joined",
    )
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    autocomplete_fields = ("country",)

    # Copia os fieldsets do UserAdmin e adiciona campos específicos
    fieldsets = list(UserAdmin.fieldsets) + [
        (
            "Informações Específicas",
            {"fields": ("credit_amount", "is_premium", "is_verified", "country")},
        ),
    ]

    readonly_fields = ("date_joined", "last_login")

    def get_full_name(self, obj):
        return obj.get_full_name() or "-"

    get_full_name.short_description = "Nome Completo"


@admin.register(ProfileAddress)
class ProfileAddressAdmin(admin.ModelAdmin):
    list_display = ("profile", "address_display", "default", "enabled")
    list_filter = ("default", "enabled", "address__city__state__country")
    search_fields = (
        "profile__username",
        "profile__email",
        "address__street",
        "address__city__name",
    )
    ordering = ("profile__username", "-default")
    autocomplete_fields = ("profile", "address")

    def address_display(self, obj):
        return str(obj.address) if obj.address else "-"

    address_display.short_description = "Endereço"


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("profile", "amount_display", "transaction_type", "created_at")
    list_filter = ("transaction_type", "created_at", "amount")
    search_fields = ("profile__username", "profile__email", "transaction_type")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("profile",)
    date_hierarchy = "created_at"

    def amount_display(self, obj):
        color = "green" if obj.amount > 0 else "red"
        return format_html('<span style="color: {};">{:+d}</span>', color, obj.amount)

    amount_display.short_description = "Quantidade"


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "images_count", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("title", "description", "author__username", "author__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    date_hierarchy = "created_at"

    def images_count(self, obj):
        return obj.uploaded_images.count()

    images_count.short_description = "Imagens"


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "profile",
        "book",
        "image_preview",
        "default",
        "variations_count",
        "created_at",
    )
    list_filter = ("default", "created_at", "book", "profile")
    search_fields = ("title", "profile__username", "profile__email", "book__title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "image_preview_large")
    autocomplete_fields = ("profile", "book", "based_on")
    date_hierarchy = "created_at"

    fieldsets = (
        ("Informações Básicas", {"fields": ("title", "image", "image_preview_large")}),
        ("Relacionamentos", {"fields": ("profile", "book", "based_on")}),
        ("Configurações", {"fields": ("default",)}),
        ("Metadados", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "Preview"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; object-fit: contain; border-radius: 8px;" />',
                obj.image.url,
            )
        return "-"

    image_preview_large.short_description = "Imagem"

    def variations_count(self, obj):
        return obj.variations.count()

    variations_count.short_description = "Variações"


# Customização do site admin
admin.site.site_header = "📖 MyDraws - Administração"
admin.site.site_title = "MyDraws Admin"
admin.site.index_title = "Painel de Administração"

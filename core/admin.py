from django.contrib import admin
from .models import Profile, CreditTransaction, UploadedImage


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'credit_amount', 'is_premium', 'is_verified', 'created_at')
    list_filter = ('is_premium', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('credit_amount', 'is_premium', 'is_verified')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Account Status', {
            'fields': ('credit_amount', 'is_premium', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'amount', 'transaction_type', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('profile__user__username', 'transaction_type')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile__user')


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'profile', 'image', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'profile__user__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile__user')

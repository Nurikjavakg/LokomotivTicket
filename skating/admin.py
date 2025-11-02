from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Payment, SessionSkating

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'role')
    list_filter = ('role',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'role'),
        }),
    )
    ordering = ('email',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('cheque_code', 'user', 'total_amount', 'status', 'date')
    list_filter = ('status', 'tariff_type', 'date')
    search_fields = ('cheque_code', 'user__email')

@admin.register(SessionSkating)
class SessionSkatingAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'payment')
    list_filter = ('date',)
    search_fields = ('payment__cheque_code',)
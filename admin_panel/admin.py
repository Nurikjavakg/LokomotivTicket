from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from users.models import User
from payment.models import Payment, SessionSkating, PaymentConfiguration

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('phone_number', 'role')}),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['cheque_code', 'user', 'amount_adult', 'amount_child', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'is_employee', 'created_at']
    search_fields = ['cheque_code', 'user__username', 'ticket_number']
    readonly_fields = ['cheque_code', 'created_at', 'updated_at']

@admin.register(SessionSkating)
class SessionSkatingAdmin(admin.ModelAdmin):
    list_display = ['payment', 'date', 'start_time', 'end_time']
    list_filter = ['date']

@admin.register(PaymentConfiguration)
class PaymentConfigurationAdmin(admin.ModelAdmin):
    list_display = ['adult_price_per_hour', 'child_price_per_hour', 'skate_rental_price', 
                   'instructor_price', 'employee_discount', 'regular_customer_discount', 'updated_at']
    
    def has_add_permission(self, request):
        return not PaymentConfiguration.objects.exists()

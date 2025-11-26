from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

User = get_user_model()

class TariffType(models.TextChoices):
    ADULT = 'ADULT', 'Взрослый'
    CHILD = 'CHILD', 'Детский'

class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Ожидает'
    COMPLETED = 'COMPLETED', 'Завершено'
    REFUNDED = 'REFUNDED', 'Возвращено'
    FAILED = 'FAILED', 'Ошибка'

class SessionStatus(models.TextChoices):
    WAITING = 'WAITING', 'Ожидает'
    IN_PROGRESS = 'IN_PROGRESS', 'В процессе'
    TIME_EXPIRED= 'TIME_EXPIRED', 'Время вышло'
    FINISHED = 'FINISHED', 'Завершен'

class PaymentConfiguration(models.Model):
    adult_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    child_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=300)
    skate_rental_price = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    instructor_price = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    employee_discount = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])  # 50%
    regular_customer_discount = models.IntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(100)])  # 10%
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Payment Configuration"
        verbose_name_plural = "Payment Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1  # Принудительно устанавливаем ID = 1
        return super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Запрещаем удаление единственной конфигурации
        pass
    
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateTimeField(auto_now_add=True)
    tariff_type = models.CharField(max_length=10, choices=TariffType.choices, default=TariffType.ADULT)
    percent = models.IntegerField(default=0)  # Скидка в процентах
    amount_adult = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    amount_child = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    hours = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    skate_rental = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # Количество коньков
    instructor_service = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cheque_code = models.CharField(max_length=20, unique=True, blank=True)
    ticket_number = models.CharField(max_length=10, blank=True)  # Номер талона Л1, Л4 и т.д.
    is_employee = models.BooleanField(default=False)
    employee_name = models.CharField(max_length=255, blank=True)
    department_name = models.CharField(max_length=150, null=True, blank=True)
    position_name = models.CharField(max_length=150, null=True, blank=True)
    skating_status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.WAITING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    fiscalized= models.BooleanField(default=False)
    fiscal_uuid = models.CharField(max_length=100,null=True,blank=True)
    fiscal_error = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.cheque_code} - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.cheque_code:
            self.cheque_code = f"CH{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)



class SessionSkating(models.Model):
    id = models.AutoField(primary_key=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='session')
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.WAITING)
    date = models.DateField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.payment.cheque_code} - {self.status}"    
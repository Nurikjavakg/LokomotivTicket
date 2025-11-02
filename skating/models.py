from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
import uuid

class Role(models.TextChoices):
    CASIER = 'CASIER', 'Кассир'
    OPERATOR = 'OPERATOR', 'Оператор'
    ADMIN = 'ADMIN', 'Админ'
    CLIENT = 'CLIENT', 'КЛИЕНТ'
    EMPLOYEE = 'EMPLOYEE', 'Сотрудник'

class TariffType(models.TextChoices):
    ADULT = 'ADULT', 'Взрослый'
    CHILD = 'CHILD', 'Детский'

class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Ожидание'
    COMPLETED = 'COMPLETED', 'Завершено'
    REFUNDED = 'REFUNDED', 'Возвращено'  

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT
    )
     # Remove the original fields we're replacing
    username = None
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    price = models.IntegerField(validators=[MinValueValidator(0)])
    date = models.DateField(auto_now_add=True)
    tariff_type = models.CharField(
        max_length=10,
        choices=TariffType.choices
    )
    percent = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0
    )
    amount_adult = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0
    )
    amount_child = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0
    )
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    cheque_code = models.BigIntegerField(unique=True)
    
    def save(self, *args, **kwargs):
        # Calculate total amount before saving
        adult_price = self.price
        child_price = self.price * 0.7  # 30% discount for children
        
        self.total_amount = (
            (adult_price * self.amount_adult) + 
            (child_price * self.amount_child)
        ) * (1 - self.percent / 100)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payment {self.cheque_code} - {self.user.email}"

class SessionSkating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='session_skating'
    )
    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    def __str__(self):
        return f"Session {self.date} - {self.start_time.strftime('%H:%M')}"
    
    @property
    def duration(self):
        return self.end_time - self.start_time
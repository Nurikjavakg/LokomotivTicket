
from django.contrib.auth.models import AbstractUser
from django.db import models



class Role(models.TextChoices):
    CASHIER = 'CASHIER', 'Кассир'
    OPERATOR = 'OPERATOR', 'Оператор'
    ADMIN = 'ADMIN', 'Админ'
    CLIENT = 'CLIENT', 'КЛИЕНТ'
    EMPLOYEE = 'EMPLOYEE', 'Сотрудник'

class User(AbstractUser):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT
    )

    @classmethod
    def create_superuser(cls, username, email, password, **extra_fields):
        extra_fields.setdefault('role', Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)
    

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
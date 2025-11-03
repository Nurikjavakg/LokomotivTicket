
from django.contrib.auth.models import AbstractUser
from django.db import models



class Role(models.TextChoices):
    CASIER = 'CASIER', 'Кассир'
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

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
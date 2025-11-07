
from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    CASHIER = 'CASHIER', 'Кассир'
    OPERATOR = 'OPERATOR', 'Оператор'
    ADMIN = 'ADMIN', 'Админ'
    CLIENT = 'CLIENT', 'Клиент'
    EMPLOYEE = 'EMPLOYEE', 'Сотрудник'


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"

    def __str__(self):
        return self.name


class User(AbstractUser):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)

    # Добавляем ссылки
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Филиал")
    position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Должность")

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
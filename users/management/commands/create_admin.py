from django.core.management.base import BaseCommand
from users.models import User, Role

class Command(BaseCommand):
    help = 'Создает администратора по умолчанию'

    def handle(self, *args, **options):

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@lokomotive.kg',
                password='Adminlokomotiv123',
                first_name ='Администратор',
                last_name = 'Системы',
                role = Role.ADMIN
            )
            self.stdout.write(
                self.style.SUCCESS('Администратор создан: admin / Adminlokomotiv123')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Администратор уже существует')
            )    
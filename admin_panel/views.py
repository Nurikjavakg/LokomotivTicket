from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from django.db import transaction
from users.models import Department, Position
from payment.models import PaymentConfiguration
from .serializers import DepartmentPositionSerializer, PaymentConfigurationSerializer

# -------------------------------------------
# Permission для проверки роли ADMIN
# -------------------------------------------
class IsAdminUserCustom(BasePermission):
    """
    Разрешение только для пользователей с role = 'ADMIN'
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN'

# -------------------------------------------
# Departments и Positions
# -------------------------------------------
class DepartmentPositionViewSet(viewsets.ViewSet):
    """
    API для одновременного создания Departments и Positions
    """
    permission_classes = [IsAuthenticated, IsAdminUserCustom]
    serializer_class = DepartmentPositionSerializer

    def list(self, request):
        departments = Department.objects.all().values('id', 'name')
        positions = Position.objects.all().values('id', 'name')
        return Response({
            'departments': list(departments),
            'positions': list(positions)
        })

    def create(self, request):
        serializer = DepartmentPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        created_departments = []
        created_positions = []

        try:
            with transaction.atomic():
                for dep_name in data.get('departments', []):
                    dep, created = Department.objects.get_or_create(name=dep_name)
                    if created:
                        created_departments.append(dep.name)

                for pos_name in data.get('positions', []):
                    pos, created = Position.objects.get_or_create(name=pos_name)
                    if created:
                        created_positions.append(pos.name)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'created_departments': created_departments,
            'created_positions': created_positions
        }, status=status.HTTP_201_CREATED)

# -------------------------------------------
# Payment Configuration
# -------------------------------------------
class PaymentConfigurationViewSet(viewsets.ModelViewSet):
    """
    API для управления ценами и скидками
    """
    queryset = PaymentConfiguration.objects.all()
    serializer_class = PaymentConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def list(self, request, *args, **kwargs):
        instance = PaymentConfiguration.objects.first()
        if not instance:
            instance = PaymentConfiguration.objects.create()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # Вместо создания — обновляем существующую конфигурацию
        instance = PaymentConfiguration.load()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

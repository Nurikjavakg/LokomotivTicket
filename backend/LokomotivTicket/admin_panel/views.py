from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from users.models import Department, Position
from payment.models import PaymentConfiguration
from .serializers import DepartmentPositionCreateSerializer, PaymentConfigurationSerializer
from rest_framework.decorators import action

# Permission для проверки роли ADMIN
class IsAdminUserCustom(BasePermission):
    """
    Разрешение только для пользователей с role = 'ADMIN'
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN'

# Payment Configuration
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

# Departments и Positions
class DepartmentPositionViewSet(viewsets.ViewSet):
    """
    POST /api/admin-panel/departments-positions/
    {
      "department_name": "Филиал ИВЦ",
      "position_name": "Инженер программист"
    }
    """
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def create(self, request):
        serializer = DepartmentPositionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dep_name = serializer.validated_data.get('department_name')
        pos_name = serializer.validated_data.get('position_name')

        result = {}

        # Обрабатываем департамент (только в Department)
        if dep_name:
            dep_clean = dep_name.strip()
            dep_obj, dep_created = Department.objects.get_or_create(name=dep_clean)
            result['department'] = {'name': dep_obj.name, 'created': dep_created}

        # Обрабатываем позицию (только в Position)
        if pos_name:
            pos_clean = pos_name.strip()
            pos_obj, pos_created = Position.objects.get_or_create(name=pos_clean)
            result['position'] = {'name': pos_obj.name, 'created': pos_created}

        # Если ни одного поля не передали — возвращаем ошибку
        if not result:
            return Response(
                {"success": False, "detail": "Не передано ни department_name, ни position_name"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class DepartmentPositionAutocompleteViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='departments')
    def departments(self, request):
        q = request.GET.get('q', '').strip()
        results = Department.objects.filter(name__icontains=q)[:10]
        return Response([{'id': d.id, 'name': d.name} for d in results])

    @action(detail=False, methods=['get'], url_path='positions')
    def positions(self, request):
        q = request.GET.get('q', '').strip()
        results = Position.objects.filter(name__icontains=q)[:10]
        return Response([{'id': p.id, 'name': p.name} for p in results])

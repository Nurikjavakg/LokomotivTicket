from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from users.models import Department, Position
from payment.models import PaymentConfiguration
from .serializers import DepartmentPositionCreateSerializer, PaymentConfigurationSerializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

    @swagger_auto_schema(
        operation_summary="Просмотр тарифы",
        operation_description="Возвращает текущую конфигурацию цен и скидок для катка",
        responses={200: PaymentConfigurationSerializer}
    )
    @action(detail=False, methods=['get'], url_path='check_tariff')
    def checkTariff(self, request, *args, **kwargs):
        instance = PaymentConfiguration.objects.first()
        if not instance:
            instance = PaymentConfiguration.objects.create()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_summary="Обновление оплаты",
        operation_description="Обновляет существующую конфигурацию цен и скидок для катка",
        responses={200: PaymentConfigurationSerializer, 400: "Ошибка валидации данных"}
    )
    @action(detail=False, methods=['put'], url_path='update_tariff')
    def updateTariff(self, request, *args, **kwargs):
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

    @swagger_auto_schema(
        operation_summary="Создать департамент и/или позицию",
        operation_description="Создаёт новый департамент и/или позицию, если их ещё нет",
        responses={201: "Данные успешно созданы", 400: "Ошибка валидации"}
    )
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
    @swagger_auto_schema(
        operation_summary="Поиск департаментов по названию",
        operation_description="Возвращает список департаментов, содержащих подстроку, переданную в параметре `q` (максимум 10 результатов).",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Часть названия департамента для поиска",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Успешный ответ: список найденных департаментов",
                examples={
                    "application/json": [
                        {"id": 1, "name": "Филиал ИВЦ"},
                        {"id": 2, "name": "Филиал ТЧ-1"}
                    ]
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='departments')
    def departments(self, request):
        q = request.GET.get('q', '').strip()
        results = Department.objects.filter(name__icontains=q)[:10]
        return Response([{'id': d.id, 'name': d.name} for d in results])

    @swagger_auto_schema(
        operation_summary="Поиск позиций по названию",
        operation_description="Возвращает список позиций (должностей), содержащих подстроку, переданную в параметре `q` (максимум 10 результатов).",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Часть названия должности для поиска",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Успешный ответ: список найденных позиций",
                examples={
                    "application/json": [
                        {"id": 1, "name": "Инженер программист"},
                        {"id": 2, "name": "Кассир"}
                    ]
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='positions')
    def positions(self, request):
        q = request.GET.get('q', '').strip()
        results = Position.objects.filter(name__icontains=q)[:10]
        return Response([{'id': p.id, 'name': p.name} for p in results])
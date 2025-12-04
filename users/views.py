from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Role
from .serializers import UserSerializer, RegisterSerializer, AdminUserCreateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Профиль пользователя',
        operation_description='Получение данных текущего аутентифицированного пользователя'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_object(self):
        return self.request.user
 
@swagger_auto_schema(
    method='post',
    operation_description="""
    Получение JWT токенов для доступа к API.
    
    **Возвращает:**
    - access: JWT токен для доступа к API (короткоживущий)
    - refresh: Токен для обновления access токена (долгоживущий)
    - user: Данные аутентифицированного пользователя
    """,
    operation_summary= 'Аутентификация пользователя',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description='Имя пользователя'
            ),
            'password': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description='Пароль',
                format='password'
            ),
        },
    ),
    responses={
        200: openapi.Response(
            description="Успешная аутентификация",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'refresh': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Refresh токен'
                    ),
                    'access': openapi.Schema(
                        type=openapi.TYPE_STRING, 
                        description='Access токен'
                    ),
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        description='Данные пользователя',
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'role': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            ),
            examples={
                "application/json": {
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "user": {
                        "id": 1,
                        "username": "admin",
                        "email": "admin@lokomotiv.kg",
                        "role": "ADMIN"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Неверные учетные данные",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Сообщение об ошибке'
                    )
                }
            ),
            examples={
                "application/json": {
                    "error": "неверные учетные данные"
                }
            }
        ),
        500: openapi.Response(
            description="Внутренняя ошибка сервера"
        )
    }
    
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username = username, password = password)

    if user:
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            'refresh': str(refresh),
            'access': str(access),
            'user': UserSerializer(user).data
        })
        
    else: 
        return Response({
            'error': 'неверные учетные данные'}, status= status.HTTP_400_BAD_REQUEST
        )

class AdminUserCreateView(generics.CreateAPIView):
    serializer_class = AdminUserCreateSerializer
    permission_classes =[permissions.IsAdminUser]
    @swagger_auto_schema(
            operation_description='Создание сотрудника Администратором',
            operation_summary='Создание сотрудника Администратором',
            request_body= AdminUserCreateSerializer,
            responses={200:openapi.Response('Сотрудник создан')}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        role = request.data.get('role')

        if role not in [Role.CASHIER, Role.OPERATOR, Role.EMPLOYEE, Role.ADMIN]:
            return Response({
                'error': "Можно создавать только Кассира, Оператора, Админа или Сотрудника"},
                status= status.HTTP_400_BAD_REQUEST
                )
        
        return super().create(request, *args, **kwargs) 
    
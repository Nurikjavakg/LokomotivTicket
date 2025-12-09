from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework_simplejwt.views import TokenRefreshView

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
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'неверные учетные данные'}, status=401)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    response = Response({
        'isAuthorized': True,
        'access': access_token,
        'user': UserSerializer(user).data
    })


    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='Lax',
        path='/',
        max_age=60 * 60 * 24 * 30
    )

    return response

@api_view(['POST'])
@permission_classes([AllowAny])  # можно и IsAuthenticated — как хочешь
def logout_view(request):

    response = Response({
        'isAuthorized': False,
        'message': 'Успешно вышли из системы'
    }, status=status.HTTP_200_OK)


    response.delete_cookie(
        key='refresh_token',
        path='/',
        domain=None
    )

    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_auth(request):
    return Response({
        'isAuthorized': True,
        'user': UserSerializer(request.user).data
    })


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):

        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {"error": "Refresh token not found in cookie"},
                status=status.HTTP_401_UNAUTHORIZED
            )


        mutable_data = request.data.copy()
        mutable_data['refresh'] = refresh_token
        request._full_data = mutable_data


        response = super().post(request, *args, **kwargs)


        if response.status_code == 200 and 'refresh' in response.data:
            response.set_cookie(
                key='refresh_token',
                value=response.data['refresh'],
                httponly=True,
                secure=True,           # на проде True
                samesite='Lax',
                path='/',
                max_age=60*60*24*30    # 30 дней
            )


        return response
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

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Role
from .serializers import UserSerializer, RegisterSerializer, AdminUserCreateSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer


    def get_object(self):
        return self.request.user
    
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username = username, password = password)

    if user:
        refresh = RefreshToken.for_user(user)

        return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        
    else: 
        return Response({
            'error': 'неверные учетные данные'}, status= status.HTTP_400_BAD_REQUEST
        )

class AdminUserCreateView(generics.CreateAPIView):
    serializer_class = AdminUserCreateSerializer
    permission_classes =[permissions.IsAdminUser]
   
    def create(self, request, *args, **kwargs):
        role = request.data.get('role')

        if role not in [Role.CASHIER, Role.OPERATOR, Role.EMPLOYEE, Role.ADMIN]:
            return Response({
                'error': "Можно создавать только Кассира, Оператора, Админа или Сотрудника"},
                status= status.HTTP_400_BAD_REQUEST
                )
        
        return super().create(request, *args, **kwargs) 
    
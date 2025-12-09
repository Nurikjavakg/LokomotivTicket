from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import login_view, check_auth,logout_view, CookieTokenRefreshView

urlpatterns = [
    path('api/auth/login/', login_view),
    path('api/auth/logout/', logout_view, name='logout'),
    path('api/auth/check/', check_auth),
    path('api/auth/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('admin/create-staff/', views.AdminUserCreateView.as_view(), name='admin-create-staff'),
]
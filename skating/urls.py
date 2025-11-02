from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionSkatingViewSet, PaymentViewSet, UserViewSet

router = DefaultRouter()
router.register(r'sessions', SessionSkatingViewSet, basename='session')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('api/', include(router.urls)),
]
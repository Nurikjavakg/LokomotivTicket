from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, SessionSkatingViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register('sessions', SessionSkatingViewSet, basename='sessions')

urlpatterns = [
    path('', include(router.urls)),
]
from rest_framework.routers import DefaultRouter
from .views import DepartmentPositionViewSet, PaymentConfigurationViewSet

router = DefaultRouter()
router.register(r'departments-positions', DepartmentPositionViewSet, basename='departments-positions')
router.register(r'payment-config', PaymentConfigurationViewSet, basename='payment-config')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter
from .views import DepartmentPositionViewSet, DepartmentPositionAutocompleteViewSet, PaymentConfigurationViewSet

router = DefaultRouter()
router.register(r'payment-config', PaymentConfigurationViewSet, basename='payment-config')
router.register(r'departments-positions', DepartmentPositionViewSet, basename='departments-positions')
router.register(r'autocomplete', DepartmentPositionAutocompleteViewSet, basename='autocomplete')

urlpatterns = router.urls
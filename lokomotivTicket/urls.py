"""
URL configuration for lokomotivTicket project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.conf import settings
from django.views.static import serve  # для Swagger в проде

from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from admin_panel.views import (
    DepartmentPositionViewSet,
    DepartmentPositionAutocompleteViewSet,
    PaymentConfigurationViewSet
)

# Домашняя страница
def home(request):
    return HttpResponse("Lokomotiv backend работает!")

# Роутеры
router = DefaultRouter()
router.register(r'payments', PaymentConfigurationViewSet, basename='payments')
router.register(r'departments-positions', DepartmentPositionViewSet, basename='departments-positions')
router.register(r'autocomplete', DepartmentPositionAutocompleteViewSet, basename='autocomplete')

# Swagger / Redoc схема
schema_view = get_schema_view(
    openapi.Info(
        title="Каток Локомотив API",
        default_version='v1',
        description="API документация для системы управления катком",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@lokomotiv.kg"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    url='http://127.0.0.1',
    permission_classes=(permissions.AllowAny,),
    validators=['ssv', 'flex'], 
)

# Основные маршруты
urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/payment/', include('payment.urls')),
    path('api/admin-panel/', include(router.urls)),
    path('api/admin-panel/', include('admin_panel.urls')),

    # Swagger + Redoc
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # Статика для Swagger в продакшене
    re_path(r'^swagger/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

# Только для разработки
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
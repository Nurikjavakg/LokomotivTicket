from rest_framework import serializers
from users.models import Department, Position
from payment.models import PaymentConfiguration

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name']

class DepartmentPositionCreateSerializer(serializers.Serializer):
    department_name = serializers.CharField(required=False, allow_blank=True)
    position_name = serializers.CharField(required=False, allow_blank=True)

class PaymentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentConfiguration
        fields = '__all__'
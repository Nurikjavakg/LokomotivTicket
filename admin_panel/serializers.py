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

class DepartmentPositionSerializer(serializers.Serializer):
    """
    Serializer для добавления одновременно Departments и Positions
    """
    departments = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False
    )
    positions = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False
    )
    
class PaymentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentConfiguration
        fields = '__all__'
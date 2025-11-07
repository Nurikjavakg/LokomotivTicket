from rest_framework import serializers
from .models import Payment, SessionSkating
from users.models import User

class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_name', 'price', 'date', 'tariff_type', 
            'percent', 'amount_adult', 'amount_child', 'hours', 
            'skate_rental', 'instructor_service', 'status', 'status_display',
            'total_amount', 'cheque_code', 'ticket_number', 'is_employee',
            'employee_name', 'created_at'
        ]
        read_only_fields = ['cheque_code', 'total_amount', 'status']

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'amount_adult', 'amount_child', 'hours', 'skate_rental',
            'instructor_service', 'ticket_number', 'is_employee', 'employee_name'
        ]
    
    def validate(self, data):
        if data['is_employee'] and not data.get('employee_name'):
            raise serializers.ValidationError("Employee name is required for employee payments")
        return data

class SessionSkatingSerializer(serializers.ModelSerializer):
    payment = serializers.StringRelatedField()

    class Meta:
        model = SessionSkating
        fields = '__all__'    
from rest_framework import serializers 
from .models import User, Payment, SessionSkating, Role, TariffType, PaymentStatus

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'price', 'date', 'tariff_type', 
            'percent', 'amount_adult', 'amount_child', 'status', 
            'total_amount', 'cheque_code'
        ]

class SessionSkatingSerializer(serializers.ModelSerializer):
    payment_details = PaymentSerializer(source='payment', read_only=True)
    
    class Meta:
        model = SessionSkating
        fields = [
            'id', 'payment', 'payment_details', 'date', 'start_time', 'end_time'
        ]
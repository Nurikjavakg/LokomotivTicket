from rest_framework import serializers
from django.utils import timezone
from .models import Payment, SessionSkating, PaymentStatus, SessionStatus
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

class OperatorSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='user.get_full_name', read_only=True)
    time_remaining = serializers.SerializerMethodField()
    session_info = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'cheque_code','amount_adult', 'amount_child',
            'hours', 'skate_rental','time_remaining',
            'ticket_number','employee_name',
            'skating_status', 'cashier_name','session_info'
        ]
    def get_time_remaining(self, obj):
       
        if (obj.skating_status == SessionStatus.IN_PROGRESS and 
            hasattr(obj, 'session') and 
            obj.session.start_time):
            
            session_end = obj.session.start_time + timezone.timedelta(hours=obj.hours)
            remaining = session_end - timezone.now()
            return max(0, int(remaining.total_seconds() / 60))
        
        
        return 0
    
    def get_session_info(self,obj):
        if hasattr(obj,'session'):
            return {
                'start_time': obj.session.start_time,
                'end_time': obj.session.end_time,
                'date':obj.session.date
            }
        return None
    

class SessionSkatingSerializer(serializers.ModelSerializer):
    payment_info = OperatorSerializer(source='payment',read_only=True)

    class Meta:
        model = SessionSkating
        fields = ['id', 'status', 'start_time', 'end_time', 'date', 'payment_info']


class ReportSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='user_get_full_name', read_only=True)
    total_visitors= serializers.SerializerMethodField()
    session_duration= serializers.SerializerMethodField()


    class Meta:
        model = Payment
        fields = [
            'id', 'cheque_code', 'cashier_name', 'amount_adult', 'amount_child',
            'total_visitors', 'hours', 'session_duration', 'skate_rental',
            'instructor_service', 'ticket_number', 'is_employee', 'employee_name',
            'total_amount', 'created_at'
        ]

    def get_total_visitors(self, obj):
        return obj.amount_adult + obj.amount_child
        
    def get_session_duration(self, obj):
        return f"{obj.hours} ч"




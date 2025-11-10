from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from datetime import datetime, timedelta
import uuid

from .models import Payment, SessionSkating
from .serializers import PaymentSerializer, PaymentCreateSerializer
from users.models import Department, Position
from .services import PaymentService, MegaPayService

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'CASHIER']:
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(user=user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_data = serializer.validated_data

        try:
            with transaction.atomic():
                # Автосоздание департамента и позиции, если не существует
                dep_name = payment_data.get('department_name')
                pos_name = payment_data.get('position_name')

                if dep_name:
                    Department.objects.get_or_create(name=dep_name)
                if pos_name:
                    Position.objects.get_or_create(name=pos_name)

                # Расчёт общей суммы
                total_amount = PaymentService.calculate_total_amount(payment_data)

                # Создаём Payment
                payment = Payment(
                    user=request.user,
                    department_name=dep_name,
                    position_name=pos_name,
                    amount_adult=payment_data['amount_adult'],
                    amount_child=payment_data['amount_child'],
                    hours=payment_data['hours'],
                    skate_rental=payment_data.get('skate_rental', 0),
                    instructor_service=payment_data.get('instructor_service', False),
                    ticket_number=payment_data.get('ticket_number', ''),
                    is_employee=payment_data.get('is_employee', False),
                    employee_name=payment_data.get('employee_name', ''),
                    total_amount=total_amount,
                    cheque_code=f"CH{uuid.uuid4().hex[:8].upper()}",
                    status='PENDING'
                )
                payment.save()

                # Создаём сессию катка
                session_date = datetime.now().date()
                start_time = datetime.now()
                end_time = start_time + timedelta(hours=payment_data['hours'])

                session = SessionSkating(
                    payment=payment,
                    date=session_date,
                    start_time=start_time,
                    end_time=end_time
                )
                session.save()

                # Инициализация оплаты через MegaPay
                payment_response = MegaPayService.initiate_payment(
                    amount=float(total_amount),
                    order_id=payment.cheque_code,
                    description=f"Каток Локомотив - {payment.ticket_number}"
                )

                if payment_response.get('success'):
                    payment.status = 'COMPLETED'
                    payment.save()

                    return Response({
                        'success': True,
                        'payment_id': payment.id,
                        'cheque_code': payment.cheque_code,
                        'total_amount': total_amount,
                        'redirect_url': payment_response.get('redirect_url'),
                        'slip_data': PaymentService.generate_slip_data(payment)
                    }, status=status.HTTP_201_CREATED)
                else:
                    payment.status = 'FAILED'
                    payment.save()
                    return Response({
                        'success': False,
                        'error': payment_response.get('error', 'Payment failed')
                    }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST) 
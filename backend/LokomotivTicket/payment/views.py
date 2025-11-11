from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Payment, SessionSkating, PaymentConfiguration
from .serializers import PaymentSerializer, PaymentCreateSerializer, OperatorSerializer, ReportSerializer
from .services import PaymentService, MegaPayService
from datetime import datetime, timedelta
from django.utils import timezone
from .models import SessionStatus,PaymentStatus
from users.models import User, Role
from django.db.models import Count, Sum, Avg, Q
from django.db import models
from django.db.models.functions import TruncDate
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


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
        
    @swagger_auto_schema(
    operation_summary="Дашборд оператора",
    operation_description="""
    Панель управления сеансами катания для оператора.
    
    Отображает сеансы в трех статусах:
    - WAITING: Готовы к началу
    - IN_PROGRESS: Активные сеансы с таймером
    - TIME_EXPIRED: Время вышло, требуется завершение
    """
)
    @action(detail=False, methods=['get'])
    def operator_dashboard(self, request):
        if request.user.role != 'OPERATOR':
            return Response ({
                'error': 'Доступна только оператора'}, status = status.HTTP_403_FORBIDDEN)
        
        try:
            in_progress_sessions= SessionSkating.objects.filter(status= SessionStatus.IN_PROGRESS)
            for session in in_progress_sessions:
                if session.start_time:  # Проверить что start_time не None
                    session_end = session.start_time + timezone.timedelta(hours=session.payment.hours)
                    if timezone.now() >= session_end:
                        session.status = SessionStatus.TIME_EXPIRED
                        session.end_time = session_end
                        session.save()
                        session.payment.skating_status = SessionStatus.TIME_EXPIRED
                        session.payment.save()
        except Exception as e:
        
            print(f"Error in auto-finish: {e}")
        
        completed_payments = Payment.objects.filter(status = PaymentStatus.COMPLETED)

        waiting = completed_payments.filter(skating_status = SessionStatus.WAITING)
        in_progress= completed_payments.filter(skating_status=SessionStatus.IN_PROGRESS)
        time_expired = completed_payments.filter(skating_status = SessionStatus.TIME_EXPIRED)

        serializer= OperatorSerializer

        return Response({
            'waiting': serializer(waiting, many=True).data,
            'in_progress': serializer(in_progress, many= True).data,
            'time_expired': serializer(time_expired, many=True).data,
        }) 
    @swagger_auto_schema(
            operation_summary='Начать сеанс катания',
            operation_description="""
    Запуск сеанса катания для оплаченного платежа.
    
    **Требуемая роль:** OPERATOR
    **Статус платежа:** COMPLETED  
    **Статус сеанса:** WAITING → IN_PROGRESS
    """
    )       
    @action(detail=True, methods=['post'])
    def start_skating(self,request,pk=None):
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({
                'error': 'Платеж не найден'
            }, status= status.HTTP_404_NOT_FOUND)

        if request.user.role != 'OPERATOR':
            return Response ({
                'error': 'Только оператор может начать сеанс'}, status= status.HTTP_403_FORBIDDEN
            )
        
        if payment.status != PaymentStatus.COMPLETED:
            return Response({'error': 'Платеж не оплачен'}, status=status.HTTP_400_BAD_REQUEST)
        
        if payment.skating_status != SessionStatus.WAITING:
            return Response({'error': 'Сеанс уже начат или завершен'}, status=status.HTTP_400_BAD_REQUEST)
       
       
        session_skating, created = SessionSkating.objects.get_or_create(
            payment=payment,
            defaults={
                'status': SessionStatus.IN_PROGRESS,
                'start_time': timezone.now(),
                'date': timezone.now().date()
            }
        )
        
        if not created:
            session_skating.status = SessionStatus.IN_PROGRESS
            session_skating.start_time = timezone.now()
            session_skating.save()
        
       
        payment.skating_status = SessionStatus.IN_PROGRESS
        payment.save()
        
        session_end = session_skating.start_time + timezone.timedelta(hours=payment.hours)
        
        return Response({
            'status': 'Катание начато',
            'session_end': session_end,
            'duration_hours': payment.hours,
            'session_id': str(session_skating.id)
        })
    


    @swagger_auto_schema(
            operation_summary='Завершить сеанс катания',
            operation_description="""
        Завершение сеанса катания для клиента с истекшим временем.
        
        **Требуемая роль:** OPERATOR
        
        **Условия:**
        - Платеж должен быть в статусе COMPLETED
        - Сеанс должен быть в статусе TIME_EXPIRED (время вышло)
        - Оператор должен физически проверить что клиент ушел
        
        **Workflow:** WAITING → IN_PROGRESS → TIME_EXPIRED → FINISHED
        """
    )
    @action(detail=True, methods=['post'])
    def finish_skating(self, request, pk=None):
        """Завершить катание (для оператора)"""
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({
                'error': 'Платеж не найден'
            }, status= status.HTTP_404_NOT_FOUND)

        
        if request.user.role != 'OPERATOR':
            return Response({'error': 'Только оператор может завершать сеансы'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        if payment.skating_status != SessionStatus.TIME_EXPIRED:
            return Response({'error': 'Можно завершать только сеансы с истекшим временем'}, status=status.HTTP_400_BAD_REQUEST)
        
       
        if hasattr(payment, 'session'):
            payment.session.status = SessionStatus.FINISHED
            payment.session.end_time = timezone.now()
            payment.session.save()
        
        
        payment.skating_status = SessionStatus.FINISHED
        payment.save()
        
        return Response({'status': 'Катание завершено'})
    
    @swagger_auto_schema(
            operation_summary='Принудительно завершить сеанс',
            operation_description='Завершение сеанса оператором'
    )
    @action(detail= True, methods=['post'])
    def force_finish_skating(self, request, pk=None):
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({'error': 'Платеж не найден'}, status= status.HTTP_404_NOT_FOUND)
        
        if request.user.role != Role.OPERATOR:
            return Response({'error': 'Только оператор может завершить сеанс'} , status= status.HTTP_403_FORBIDDEN)

        if payment.skating_status not in [SessionStatus.IN_PROGRESS, SessionStatus.TIME_EXPIRED]:
            return Response({'error':'Можно завершить только активные сеансы'}, status= status.HTTP_400_BAD_REQUEST)

        if hasattr (payment, 'session'):
            payment.session.status = SessionStatus.FINISHED,
            payment.session.end_time = timezone.now()
            payment.save()

        previous_status = payment.skating_status
        payment.skating_status = SessionStatus.FINISHED
        payment.save()

        return Response({
            'status': 'Сеанс принудительно завершен',
            'payment_id': payment.id,
            'previous_status': previous_status,
            'reason': 'Принудительное завершение оператором'
        })





    

    @swagger_auto_schema(
            operation_summary='Получить отчет',
            operation_description='Получение детального отчета по завершенным платежам'
    )
    @action(detail=False, methods=['get'], url_path='session-report')
    def get_all_finished_payment(self, request):

        if request.user.role != Role.ADMIN:
            return Response ({'error':'Доступна только администратором'},status= status.HTTP_403_FORBIDDEN)
        
        from_date= request.GET.get('from_date')
        to_date= request.GET.get('to_date')

        finished_skates= Payment.objects.filter(
            skating_status = SessionStatus.FINISHED,
            status= PaymentStatus.COMPLETED
        )

        if from_date:
            finished_skates = finished_skates.filter(created_at__gte=from_date)
        if to_date:
            finished_skates = finished_skates.filter(created_at__lte=to_date)

        main_stats= finished_skates.aggregate(
            total_sessions=Count('id'),
            total_revenue=Sum('total_amount'),
            average_session_price = Avg('total_amount'),
            total_hours=Sum('hours'),
            total_skaters =Sum('amount_adult')+Sum('amount_child'),
            total_skate_rentals= Sum('skate_rental'),
            instructor_sessions=Count('id',filter=models.Q(instructor_service=True))
            )

        daily_stats= finished_skates.annotate(
            report_date= TruncDate('created_at'),
            ).values('report_date').annotate(
            sessions= Count('id'),
            revenue= Sum('total_amount'),
            avarage_price= Avg('total_amount')
            )

        cashier_stats = finished_skates.values(
            'user__id', 'user__first_name', 'user__last_name'
            ).annotate(
            sessions = Count('id'),
            revenue= Sum('total_amount'),
            ).order_by('-revenue')

        return Response({
            'period':{
                'from_date': from_date,
                'to_date': to_date
                },
                'summary': main_stats,
                'daily_breakdown': list(daily_stats),
                'cashier_perfomance':list(cashier_stats),
            })
            
    
    @swagger_auto_schema(
        operation_description="Отчет за последнюю неделю",
        operation_summary='Получение отчета за последнюю неделю',
        responses={200: openapi.Response('Недельный отчет'),
        }
    )
    @action(detail=False, methods=['get'], url_path='weekly-report')
    def get_weekly_report(self, request):
        """Отчет за последнюю неделю"""
        return self._auto_generate_report(7,'Неделя')
    
    @swagger_auto_schema(
        operation_description="Отчет за последний месяц",
        operation_summary='Получение отчета за последний месяц',
        responses={200: openapi.Response('Месячный отчет')}
    )
    @action(detail=False, methods=['get'], url_path='monthly-report')
    def get_monthly_report(self, request):
        """Отчет за последний месяц"""
        return self._auto_generate_report(30,'Месяц')
    
    @swagger_auto_schema(
        operation_description="Отчет за последний год",
        operation_summary='Получение отчета за последний год',
        responses={200: openapi.Response('Годовой отчет')}
    )
    @action(detail=False, methods=['get'], url_path='yearly-report')
    def get_yearly_report(self, request):
        """Отчет за последний год""" 
        return self._auto_generate_report(365,'Год')
        
    

    def _auto_generate_report(self,days_back, period_name):
        if self.request.user.role != Role.ADMIN:
            return Response ({'error': 'Доступно только администратором'}, status= status.HTTP_403_FORBIDDEN)
        
        
        
        today = timezone.now().date()
        from_date = today - timezone.timedelta(days=days_back)

        finished_skates = Payment.objects.filter(
            skating_status = SessionStatus.FINISHED,
            status = PaymentStatus.COMPLETED,
            created_at__gte= from_date,
            created_at__lte = today
        )

        main_stats= finished_skates.aggregate(
            total_sessions=Count('id'),
            total_revenue=Sum('total_amount'),
            average_session_price = Avg('total_amount'),
            total_hours=Sum('hours'),
            total_skaters =Sum('amount_adult')+Sum('amount_child'),
            total_skate_rentals= Sum('skate_rental'),
            instructor_sessions=Count('id',filter=models.Q(instructor_service=True))
            )


        cashier_stats = finished_skates.values(
            'user__id', 'user__first_name', 'user__last_name'
            ).annotate(
            session = Count('id'),
            revenue= Sum('total_amount'),
            ).order_by('-revenue')

        return Response({
            'period':{
                'from_date': from_date,
                'to_date': today
                },
                'summary': main_stats,
                'cashier_perfomance':list(cashier_stats)
            })
    




        




        
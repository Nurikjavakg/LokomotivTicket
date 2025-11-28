from requests import session
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.status import HTTP_404_NOT_FOUND

from .fiscal import logger
from .models import Payment, SessionSkating, PaymentConfiguration
from .serializers import PaymentSerializer, PaymentCreateSerializer, OperatorSerializer, ReportSerializer, \
    OperatorSerializerOne
from .models import Payment, SessionSkating
from .serializers import PaymentSerializer, PaymentCreateSerializer, OperatorSerializer, OperatorSerializerOne, OperatorSerializerWaiting
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
from .models import Payment, SessionSkating
from .serializers import PaymentSerializer, PaymentCreateSerializer
from users.models import Department, Position
from .services import PaymentService, MegaPayService
import uuid
from django.http import JsonResponse

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        return Response({'detail': 'Method not allowed'}, status=405)

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, pk=None):
        return Response({'detail': 'Use /get-session/ instead'}, status=405)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, pk=None):
        return Response({'detail': 'Method not allowed'}, status=405)

    @swagger_auto_schema(auto_schema=None)
    def partial_update(self, request, pk=None):
        return Response({'detail': 'Method not allowed'}, status=405)

    @swagger_auto_schema(auto_schema=None)
    def destroy(self, request, pk=None):
        return Response({'detail': 'Method not allowed'}, status=405)



    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'CASHIER']:
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(user=user).order_by('-created_at')

    @swagger_auto_schema(
        operation_summary='Получение сеанса по ID',
        operation_description='Возвращает данные платежа и статус сеанса катания'
    )
    @action(detail=True, methods=['get'], url_path='get-session')
    def get_session_by_id(self,request, pk=None):

        try:
            payment = Payment.objects.select_related('session').get(id=pk)
        except Payment.DoesNotExist:
            return Response ({'error': 'Платеж не найден'}, status= status.HTTP_404_NOT_FOUND)

        serializer = OperatorSerializerOne(payment)
        if payment.skating_status == SessionStatus.WAITING:
            serializer = OperatorSerializerWaiting(payment)
        return Response(serializer.data,status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    @swagger_auto_schema(
        operation_summary="Создать оплату за каток",
        operation_description="Этот endpoint используется для создания новой записи об оплате катания на катке",
        responses={
            201: openapi.Response("Успешное создание оплаты", PaymentSerializer),
            400: "Ошибка при создании оплаты (например, сотрудник уже был сегодня)"
        }
    )
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

                # 🔹 Проверяем, если это сотрудник
                is_employee = payment_data.get('is_employee', False)
                employee_name = payment_data.get('employee_name', '')
                # Инициализируем переменную здесь
                already_exists = False
                if is_employee and employee_name:
                 today = timezone.now().date()

                # Проверяем, был ли этот сотрудник сегодня
                 existing_payment = Payment.objects.filter(
                      is_employee=True,
                      employee_name=employee_name,
                      created_at__date=today,
                      status__in=['PENDING', 'COMPLETED']
                 ).order_by('-created_at').first()

                 if existing_payment:
                    visit_time = existing_payment.created_at.strftime('%H:%M:%S')
                    return Response({
                     'success': False,
                     'error': 'Сотрудник уже был сегодня на катке.',
                     'employee_name': employee_name,
                     'visited_at': visit_time
                     }, status=status.HTTP_400_BAD_REQUEST)

                # Расчёт общей суммы
                amounts = PaymentService.calculate_total_amount(payment_data)
                total_amount = amounts['total'] 

                # Берём ticket_number из запроса
                ticket_number = payment_data.get('ticket_number', '')

                # Добавляем "Л" спереди, если ещё нет
                ticket_number_raw = payment_data.get('ticket_number', '')
                ticket_number = f"Л{ticket_number_raw}"  

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
                    ticket_number=ticket_number, 
                    is_employee=payment_data.get('is_employee', False),
                    employee_name=payment_data.get('employee_name', ''),
                    total_amount=total_amount,
                    cheque_code=f"CH{uuid.uuid4().hex[:8].upper()}",
                    status='PENDING'
                )
                payment.save()

                # Инициализация оплаты через MegaPay
                payment_response = MegaPayService.initiate_payment(
                    amount=float(total_amount),
                    order_id=payment.cheque_code,
                    description=f"Каток Локомотив - {payment.ticket_number}"
                )

                if payment_response.get('success'):
                    payment.status = 'COMPLETED'
                    payment.save()

                    from .fiscal import fiscalize_payment

                    fiscal_result = fiscalize_payment(payment)
                    if not fiscal_result["success"] and not fiscal_result.get("already_done"):
                        logger.warning(f"Не удалось выбить чек для {payment.cheque_code}: {fiscal_result['error']}")

                    return Response({
                       "category": "Сотрудник" if payment.is_employee else "Обычный клиент",
                       "employee_name": payment.employee_name or "",
                       "department_name": payment.department_name or "",
                       "position_name": payment.position_name or "",
                       "ticket_number": payment.ticket_number,

                       "hours": {
                           "value": amounts['hours'],
                           "hint": "Количество часов"
                      },
                      "adult_price_per_hour": {
                         "value": float(amounts['adult_price_per_hour']),
                           "hint": "Цена за взрослого"
                       },
                       "adult_count": {
                           "value": amounts['adult_count'],
                           "hint": "Количество взрослых"
                       },
                       "child_price_per_hour": {
                           "value": float(amounts['child_price_per_hour']),
                           "hint": "Цена за ребенка"
                       },
                       "child_count": {
                           "value": amounts['child_count'],
                           "hint": "Количество детей"
                       },
                       "skate_rental_count": {
                           "value": amounts['skate_rental_count'],
                           "hint": "Коньков в аренду"
                       },
                       "skate_total": {
                           "value": float(amounts['skate_total']),
                           "hint": "Цена за аренду коньков"
                       },
                       "instructor_used": amounts['instructor_used'],
                       "instructor_total": {
                           "value": float(amounts['instructor_total']),
                           "hint": "Цена за инструктора"
                       },
                       "discount_percent": {
                           "value": float(amounts['discount_percent']),
                           "hint": "Скидка"
                       },
                       "total_amount": {
                           "value": float(amounts['total']),
                           "hint": "Общая сумма"
                       }
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
        if request.user.role != 'OPERATOR' and request.user.role != 'ADMIN':
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
        serializerOne=OperatorSerializerOne

        data = {
            'waiting': serializer(waiting, many=True).data,
            'in_progress': serializer(in_progress, many=True).data,
            'time_expired': serializerOne(time_expired, many=True).data,
        }

        response = Response(data)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
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

        if request.user.role != Role.OPERATOR and request.user.role != Role.ADMIN:
            return Response ({
                'error': 'Только оператор или администратор может начать сеанс'}, status= status.HTTP_403_FORBIDDEN
            )
        
        if payment.status != PaymentStatus.COMPLETED:
            return Response({'error': 'Платеж не оплачен'}, status=status.HTTP_400_BAD_REQUEST)
        
        if payment.skating_status != SessionStatus.WAITING:
            return Response({'error': 'Сеанс уже начат или завершен'}, status=status.HTTP_400_BAD_REQUEST)\

        if SessionSkating.objects.filter(payment=payment).exists():
            return Response({
                'error': 'Сессия уже создана для этого платежа'
            }, status=status.HTTP_400_BAD_REQUEST)
       
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=payment.hours)

        session = SessionSkating(
            payment = payment,
            status= SessionStatus.IN_PROGRESS,
            date= timezone.now(),
            start_time= start_time,
            end_time= end_time,
            created_at= timezone.now()

        )
        payment.skating_status = SessionStatus.IN_PROGRESS
        payment.save()
        session.save()
        
        return Response({
            'status': 'Катание начато',
            'session_end': end_time,
            'duration_hours': payment.hours,
            'session_id': str(session.id)
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

        
        if request.user.role != Role.OPERATOR and request.user.role != Role.ADMIN:
            return Response({'error': 'Только оператор или администратор может завершать сеансы'},
                          status=status.HTTP_403_FORBIDDEN)
        
        if payment.skating_status != SessionStatus.TIME_EXPIRED:
            return Response({'error': 'Можно завершать только сеансы с истекшим временем'}, status=status.HTTP_400_BAD_REQUEST)


        if hasattr(payment, 'session'):
            payment.session.status = SessionStatus.FINISHED
            payment.session.end_time = timezone.now()
            payment.session.save()

        session = payment.session

        session.status = SessionStatus.FINISHED
        session.save()
        
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
        
        if request.user.role != Role.OPERATOR and request.user.role != Role.ADMIN:
            return Response({'error': 'Только оператор или администратор может завершить сеанс'} , status= status.HTTP_403_FORBIDDEN)

        if payment.skating_status not in [SessionStatus.IN_PROGRESS, SessionStatus.TIME_EXPIRED]:
            return Response({'error':'Можно завершить только активные сеансы'}, status= status.HTTP_400_BAD_REQUEST)

        if hasattr (payment, 'session'):
            payment.session.status = SessionStatus.FINISHED
            payment.session.end_time = timezone.now()
            payment.save()

        session =payment.session

        session.status = SessionStatus.FINISHED
        session.end_time = timezone.now()
        session.save()

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
    
    @swagger_auto_schema(
    operation_summary="Обновить платёж по ID",
    operation_description="""
    Позволяет изменить платёж **по ID**, но только если это последний платёж пользователя.
    Доступно только ролям **ADMIN** или **CASHIER**.

    ❗ Ограничения:
    - Можно обновлять только последний платёж.
    - Нельзя обновлять чужие платежи.
    - Нельзя обновлять завершённые платежи (COMPLETED или FAILED).
    """,
    responses={
        200: openapi.Response("Платёж успешно обновлён", PaymentSerializer),
        400: "Ошибка валидации или нельзя обновить этот платёж",
        404: "Платёж не найден"
    }
)
    @action(detail=True, methods=['put'], url_path='update-payment')
    def update_payment(self, request, pk=None):
     user = request.user

     if user.role not in ['ADMIN', 'CASHIER']:
        return Response({
            'error': 'Только администратор или кассир могут изменять оплату.'
        }, status=status.HTTP_403_FORBIDDEN)

    # 🔍 Ищем платёж по ID
     try:
        payment = Payment.objects.get(id=pk)
     except Payment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Платёж с таким ID не найден.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 🔥 Получаем последний платёж
     latest_payment = Payment.objects.order_by('-created_at').first()

    # 🔒 Разрешено обновлять только последний платёж
     if payment.id != latest_payment.id:
        return Response({
            'success': False,
            'error': 'Можно обновлять только последний платеж.'
        }, status=status.HTTP_400_BAD_REQUEST)

     # Копируем данные запроса для модификации
     data = request.data.copy()
    
    # Добавляем "Л" к номеру талона
     ticket_number_raw = data.get('ticket_number', '')
     if ticket_number_raw and not ticket_number_raw.startswith('Л'):
        data['ticket_number'] = f"Л{ticket_number_raw}"

     serializer = PaymentCreateSerializer(payment, data=data, partial=True)
     serializer.is_valid(raise_exception=True)
     

     try:
        with transaction.atomic():
            # Пересчёт суммы
            updated_data = serializer.validated_data
            amounts = PaymentService.calculate_total_amount(updated_data)

            # Обновляем общую сумму
            updated_data['total_amount'] = amounts['total']
            
            # Сохраняем через сериализатор (один раз!)
            serializer.save()
            return Response({
                'success': True,
                'message': 'Платёж успешно обновлён.'
            }, status=status.HTTP_200_OK)

     except Exception as e:
        return Response({
            'success': False,
            'error': f'Ошибка при обновлении: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
       
    @swagger_auto_schema(
        operation_summary="Получить последний платеж",
        operation_description="Возвращает данные только последнего платежа: номер талона, время оплаты и сумму",
        responses={
            200: openapi.Response("Последний платеж найден"),
            404: "Платеж не найден"
        }
    )
    @action(detail=False, methods=['get'], url_path='last-payment')
    def get_last_payment(self, request):
        """
        Получение последнего платежа.
        """
        latest_payment = Payment.objects.order_by('-created_at').first()
        if not latest_payment:
            return Response({
                'success': False,
                'error': 'Платежи не найдены'
            }, status=HTTP_404_NOT_FOUND)
        
        # Расчёт суммы для корректного JSON
        amounts = PaymentService.calculate_total_amount({
            'amount_adult': latest_payment.amount_adult,
            'amount_child': latest_payment.amount_child,
            'hours': latest_payment.hours,
            'skate_rental': latest_payment.skate_rental,
            'instructor_service': latest_payment.instructor_service,
            'is_employee': latest_payment.is_employee
        })

        data = {
            "id": latest_payment.id,
            "category": "Сотрудник" if latest_payment.is_employee else "Обычный клиент",
            "employee_name": latest_payment.employee_name or "",
            "department_name": latest_payment.department_name or "",
            "position_name": latest_payment.position_name or "",
            "ticket_number": latest_payment.ticket_number,
            
            "hours": {
                "value": amounts['hours'],
                "hint": "Количество часов"
            },
            "adult_price_per_hour": {
                "value": float(amounts['adult_price_per_hour']),
                "hint": "Цена за взрослого"
            },
            "adult_count": {
                "value": amounts['adult_count'],
                "hint": "Количество взрослых"
            },
            "child_price_per_hour": {
                "value": float(amounts['child_price_per_hour']),
                "hint": "Цена за ребенка"
            },
            "child_count": {
                "value": amounts['child_count'],
                "hint": "Количество детей"
            },
            "skate_rental_count": {
                "value": amounts['skate_rental_count'],
                "hint": "Коньков в аренду"
            },
            "skate_total": {
                "value": float(amounts['skate_total']),
                "hint": "Цена за аренду коньков"
            },
            "instructor_used": amounts['instructor_used'],
            "instructor_total": {
                "value": float(amounts['instructor_total']),
                "hint": "Цена за инструктора"
            },
            "discount_percent": {
                "value": float(amounts['discount_percent']),
                "hint": "Скидка"
            },
            "total_amount": {
                "value": float(amounts['total']),
                "hint": "Общая сумма"
            }
        }
    
        return Response(data, status=status.HTTP_200_OK)
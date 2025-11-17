from .models import PaymentConfiguration
from decimal import Decimal
import requests
import json

class PaymentService:
    @staticmethod
    def calculate_total_amount(payment_data):
        # Получаем конфигурацию цен
        config = PaymentConfiguration.objects.first()
        if not config:
            config = PaymentConfiguration.objects.create()
        
        # Данные из запроса
        amount_adult = payment_data['amount_adult']
        amount_child = payment_data['amount_child']
        hours = payment_data['hours']
        skate_rental = payment_data.get('skate_rental', 0)
        instructor_service = payment_data.get('instructor_service', False)
        is_employee = payment_data.get('is_employee', False)
        
        adult_price = config.adult_price_per_hour
        child_price = config.child_price_per_hour

        # Скидка %
        discount_percent = config.employee_discount if is_employee else config.regular_customer_discount

        # Общее количество посетителей
        total_people = amount_adult + amount_child
        discountable_people = min(total_people, 3)  # скидка только на первых 3
        nondiscount_people = total_people - discountable_people

        # Разделяем скидку на взрослых и детей
        disc_adult = min(amount_adult, discountable_people)
        disc_child = max(discountable_people - disc_adult, 0)

        nondisc_adult = amount_adult - disc_adult
        nondisc_child = amount_child - disc_child

        # Считаем тарифы
        adult_rate = adult_price * hours
        child_rate = child_price * hours

        # Сумма со скидкой
        discount_multiplier = (1 - Decimal(discount_percent) / 100)
        adult_discounted_total = disc_adult * adult_rate * discount_multiplier
        child_discounted_total = disc_child * child_rate * discount_multiplier

        # Сумма без скидки
        adult_nondiscount_total = nondisc_adult * adult_rate
        child_nondiscount_total = nondisc_child * child_rate

        # Доп. услуги
        skate_total = skate_rental * config.skate_rental_price
        instructor_total = config.instructor_price if instructor_service else Decimal(0)

        # Общая сумма
        total_after_discount = (
            adult_discounted_total + child_discounted_total +
            adult_nondiscount_total + child_nondiscount_total +
            skate_total + instructor_total
        )

        return {
            'total': total_after_discount,
            'discount_percent': discount_percent,
            'adult_count': amount_adult,
            'child_count': amount_child,
            'hours': hours,
            'skate_rental_count': skate_rental,
            'instructor_used': instructor_service,
            'adult_total': adult_discounted_total + adult_nondiscount_total,
            'child_total': child_discounted_total + child_nondiscount_total,
            'skate_total': skate_total,
            'instructor_total': instructor_total,
            'adult_price_per_hour': adult_price,
            'child_price_per_hour': child_price
        }

    @staticmethod
    def generate_slip_data(payment):
        config = PaymentConfiguration.objects.first()
        
        slip_data = {
            'cheque_code': payment.cheque_code,
            'ticket_number': payment.ticket_number,
            'date': payment.created_at.strftime('%d.%m.%Y %H:%M'),
            'adult_count': payment.amount_adult,
            'child_count': payment.amount_child,
            'hours': payment.hours,
            'skate_rental': payment.skate_rental,
            'instructor_service': 'Да' if payment.instructor_service else 'Нет',
            'is_employee': payment.is_employee,
            'employee_name': payment.employee_name,
            'total_amount': float(payment.total_amount),
            'prices': {
                'adult_per_hour': float(config.adult_price_per_hour),
                'child_per_hour': float(config.child_price_per_hour),
                'skate_rental': float(config.skate_rental_price),
                'instructor': float(config.instructor_price),
            }
        }
        
        return slip_data


class MegaPayService:
    BASE_URL = "https://api.megapay.kz"  # Замените на реальный URL API
    
    @staticmethod
    def initiate_payment(amount, order_id, description):
        """
        Имитация интеграции с платежным терминалом MegaPay
        В реальной реализации здесь будет HTTP запрос к API MegaPay
        """
        try:
            # Имитация успешного платежа
            # В реальном сценарии:
            # response = requests.post(
            #     f"{MegaPayService.BASE_URL}/payment/initiate",
            #     json={
            #         'amount': amount,
            #         'order_id': order_id,
            #         'description': description,
            #         'merchant_id': 'your_merchant_id',
            #         'signature': 'your_signature'
            #     },
            #     headers={'Content-Type': 'application/json'}
            # )
            
            # return response.json()
            
            # Имитация ответа
            return {
                'success': True,
                'transaction_id': f"MP{order_id}",
                'redirect_url': f"https://megapay.kz/payment/{order_id}",
                'status': 'completed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def check_payment_status(transaction_id):
        """
        Проверка статуса платежа
        """
        try:
            # Имитация проверки статуса
            # response = requests.get(
            #     f"{MegaPayService.BASE_URL}/payment/status/{transaction_id}"
            # )
            # return response.json()
            
            return {
                'success': True,
                'status': 'completed'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
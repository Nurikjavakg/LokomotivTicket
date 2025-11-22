# payment/fiscal.py
import requests
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
EKASSA_HOST = getattr(settings, 'EKASSA_HOST', 'https://ofddev.ekassa.kg')
EKASSA_EMAIL = getattr(settings, 'EKASSA_EMAIL', 'ekassa@tmg.kg')
EKASSA_PASSWORD = getattr(settings, 'EKASSA_PASSWORD', 'ekassa@tmg.kg')
EKASSA_FISCAL_NUMBER = getattr(settings, 'EKASSA_FISCAL_NUMBER', '0000003213047999')

# Кэш токена
_token_cache: dict[str, Optional[str | datetime]] = {
    'token': None,
    'expires_at': None
}


def _get_token() -> Optional[str]:
    """Получить токен: FORCE_TOKEN → кэш → login"""
    # 1. FORCE_TOKEN (для теста)
    if getattr(settings, 'EKASSA_FORCE_TOKEN', None):
        token = settings.EKASSA_FORCE_TOKEN
        logger.info(f"eKassa: используем FORCE_TOKEN: {token[:30]}...")
        return token

    # 2. Кэш
    now = datetime.now()
    if (_token_cache['token'] and
        isinstance(_token_cache['expires_at'], datetime) and
        _token_cache['expires_at'] > now):
        return _token_cache['token']

    # 3. Авторизация
    url = f"{EKASSA_HOST}/api/auth/login"
    payload = {"email": EKASSA_EMAIL, "password": EKASSA_PASSWORD}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get('access_token') or data.get('token')
        if not token:
            raise ValueError("Token not found in response")

        _token_cache['token'] = token
        _token_cache['expires_at'] = now + timedelta(hours=1)
        logger.info("eKassa: новый токен получен через login")
        return token
    except Exception as e:
        logger.error(f"eKassa: ошибка авторизации: {e}")
        return None


def open_shift() -> bool:
    """Открывает смену (если нужно)"""
    token = _get_token()
    if not token:
        logger.error("open_shift: нет токена")
        return False

    url = f"{EKASSA_HOST}/api/shift_open_by_fiscal_number"
    payload = {
        "fiscal_number": EKASSA_FISCAL_NUMBER,
        "html": True,
        "css": True
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            logger.info("Смена успешно открыта")
            return True
        else:
            logger.error(f"Ошибка открытия смены: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.exception("open_shift: запрос упал")
        return False


def fiscalize_payment(payment):
    """Отправляет чек в eKassa"""
    if payment.fiscalized:
        logger.info(f"Чек уже выбит: {payment.cheque_code}")
        return {"success": True, "already_done": True}

    # === Загружаем конфиг ===
    try:
        from .models import PaymentConfiguration
        config = PaymentConfiguration.load()
    except Exception as e:
        return {"success": False, "error": f"Config error: {e}"}

    # === Формируем товары ===
    goods = []


    if payment.amount_adult > 0:
        price_per_hour = float(config.adult_price_per_hour)
        total_hours = payment.amount_adult * payment.hours
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Билет взрослый × {payment.amount_adult} × {payment.hours}ч",
            "price": price_per_hour,
            "quantity": total_hours,
            "unit": "шт.",
            "st": 0,
            "vat": 0
        })


    if payment.amount_child > 0:
        price_per_hour = float(config.child_price_per_hour)
        total_hours = payment.amount_child * payment.hours
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Билет детский × {payment.amount_child} × {payment.hours}ч",
            "price": price_per_hour,
            "quantity": total_hours,
            "unit": "шт.",
            "st": 0,
            "vat": 0
        })


    if payment.skate_rental > 0:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Прокат коньков × {payment.skate_rental}",
            "price": float(config.skate_rental_price),
            "quantity": payment.skate_rental,
            "unit": "шт.",
            "st": 0,
            "vat": 0
        })


    if payment.instructor_service:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": "Услуга инструктора",
            "price": float(config.instructor_price),
            "quantity": 1,
            "unit": "шт.",
            "st": 0,
            "vat": 0
        })


    if payment.percent > 0:
        subtotal = sum(g["price"] * g["quantity"] for g in goods)
        discount = subtotal * (payment.percent / 100)
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Скидка {payment.percent}%",
            "price": -discount,
            "quantity": 1,
            "unit": "шт.",
            "st": 0,
            "vat": 0
        })

    # === Клиент ===
    customer_contact = None
    if payment.user.email:
        customer_contact = payment.user.email
    elif hasattr(payment.user, 'profile') and payment.user.profile.phone:
        customer_contact = payment.user.profile.phone

    # === Payload ===
    payload = {
        "fiscal_number": EKASSA_FISCAL_NUMBER,
        "txt": True,
        "cash": False,
        "operation": "INCOME",
        "received": float(payment.total_amount),
        "goods": goods
    }
    if customer_contact:
        payload["customerContact"] = customer_contact

    # === ОТКРЫТИЕ СМЕНЫ (опционально) ===
    # Раскомментируй, если Эламан скажет, что нужно
    # if not open_shift():
    #     return {"success": False, "error": "Не удалось открыть смену"}

    # === Отправка чека ===
    token = _get_token()
    if not token:
        return {"success": False, "error": "Auth failed"}

    url = f"{EKASSA_HOST}/api/v2/receipt"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"Отправка чека в eKassa: {payment.cheque_code}, сумма: {payment.total_amount}")
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        result = resp.json()

        if resp.status_code == 200 and (result.get("success") or "id" in result):
            fiscal_id = result.get("id") or result.get("uuid")
            payment.fiscalized = True
            payment.fiscal_uuid = fiscal_id
            payment.save(update_fields=['fiscalized', 'fiscal_uuid'])
            logger.info(f"Чек успешно выбит: {payment.cheque_code} | ID: {fiscal_id}")
            return {"success": True, "fiscal_id": fiscal_id}
        else:
            error = result.get("message") or result.get("error") or "Unknown"
            payment.fiscal_error = f"eKassa: {error}"
            payment.save(update_fields=['fiscal_error'])
            logger.error(f"eKassa error: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        payment.fiscal_error = error_msg
        payment.save(update_fields=['fiscal_error'])
        logger.exception("eKassa: запрос упал")
        return {"success": False, "error": error_msg}
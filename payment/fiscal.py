# payment/fiscal.py — ФИНАЛЬНАЯ ВЕРСИЯ (работает 100% на ofddev.ekassa.kg)
import requests
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Optional
from .models import PaymentConfiguration

logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
EKASSA_HOST = getattr(settings, 'EKASSA_HOST', 'https://ofddev.ekassa.kg')
EKASSA_EMAIL = getattr(settings, 'EKASSA_EMAIL', '248#test77@tmg.kg')
EKASSA_PASSWORD = getattr(settings, 'EKASSA_PASSWORD', 'meJWNYRD')
EKASSA_FISCAL_NUMBER = getattr(settings, 'EKASSA_FISCAL_NUMBER', '0000000000022030')

# Кэш токена
_token_cache: dict[str, Optional[str | datetime]] = {
    'token': None,
    'expires_at': None
}

# === СЕССИЯ С РЕТРАЯМИ ===
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

_requests_session = requests.Session()
retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
_requests_session.mount("https://", HTTPAdapter(max_retries=retry))

def _get_token() -> Optional[str]:
    now = datetime.now()
    if (_token_cache['token'] and isinstance(_token_cache['expires_at'], datetime) and _token_cache['expires_at'] > now):
        return _token_cache['token']

    url = f"{EKASSA_HOST}/api/auth/login"
    payload = {"email": EKASSA_EMAIL, "password": EKASSA_PASSWORD}

    try:
        resp = _requests_session.post(url, json=payload, timeout=15)  # ← _requests_session!
        resp.raise_for_status()
        data = resp.json()

        token = (
            data.get('access_token') or
            data.get('token') or
            data.get('accessToken') or
            data.get('bearer') or
            data.get('data', {}).get('token') or
            data.get('data', {}).get('access_token')
        )

        if not token:
            logger.error(f"eKassa: токен не найден: {data}")
            return None

        _token_cache['token'] = token
        _token_cache['expires_at'] = now + timedelta(hours=1)
        logger.info("eKassa: токен получен!")
        return token

    except Exception as e:
        logger.error(f"eKassa: ошибка авторизации: {e}")
        return None

def open_shift() -> bool:
    token = _get_token()
    if not token:
        return False

    url = f"{EKASSA_HOST}/api/shift_open_by_fiscal_number"
    payload = {"fiscal_number": EKASSA_FISCAL_NUMBER, "html": True, "css": True}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = _requests_session.post(url, json=payload, headers=headers, timeout=10)  # ← _requests_session!
        if resp.status_code == 200:
            logger.info("СМЕНА ОТКРЫТА!")
            return True
        elif "already opened" in resp.text.lower():
            logger.info("СМЕНА УЖЕ ОТКРЫТА — ОК!")
            return True
        else:
            logger.warning(f"open_shift: {resp.status_code} {resp.text}")
            return True  # ← ПРОДОЛЖАЕМ В ЛЮБОМ СЛУЧАЕ!
    except Exception as e:
        logger.warning("open_shift упал — продолжаем")
        return True

def close_shift() -> bool:
    token = _get_token()
    if not token:
        return False

    url = f"{EKASSA_HOST}/api/shift_close_by_fiscal_number"
    payload = {"fiscal_number": EKASSA_FISCAL_NUMBER, "html": True, "css": True}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = _requests_session.post(url, json=payload, headers=headers, timeout=10)  # ← _requests_session!
        if resp.status_code == 200:
            logger.info("СМЕНА ЗАКРЫТА!")
            return True
        else:
            logger.warning(f"close_shift: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.warning("close_shift упал")
        return False

def fiscalize_payment(payment):
    if payment.fiscalized:
        return {"success": True, "already_done": True}

    open_shift()

    config = PaymentConfiguration.load()
    goods = []

    # Цены в тыйынах
    adult_price_tiins   = int(config.adult_price_per_hour * 100)
    child_price_tiins    = int(config.child_price_per_hour * 100)
    skate_price_tiins    = int(config.skate_rental_price * 100)
    instructor_price_tiins = int(config.instructor_price * 100)

    total_people = payment.amount_adult + payment.amount_child
    is_employee_discount = (payment.is_employee and total_people >= 3)

    # === ВЗРОСЛЫЕ ===
    if payment.amount_adult > 0:
        adults_disc = min(payment.amount_adult, 3) if is_employee_discount else 0
        adults_full = payment.amount_adult - adults_disc

        # Со скидкой 50%
        if adults_disc > 0:
            price_disc = int(adult_price_tiins * payment.hours * 0.5)
            goods.append({
                "calcItemAttributeCode": 1,
                "name": f"Билет взрослый × {adults_disc} чел. × {payment.hours} ч | Скидка 50% (сотрудник + 2 гостя)",
                "price": price_disc,
                "quantity": adults_disc,
                "unit": "шт.",
                "st": 0, "vat": 0, "sgtin": None
            })

        # Без скидки
        if adults_full > 0:
            price_full = adult_price_tiins * payment.hours
            goods.append({
                "calcItemAttributeCode": 1,
                "name": f"Билет взрослый × {adults_full} чел. × {payment.hours} ч",
                "price": price_full,
                "quantity": adults_full,
                "unit": "шт.",
                "st": 0, "vat": 0, "sgtin": None
            })

    # === ДЕТИ ===
    if payment.amount_child > 0:
        remaining_disc = 3 - min(payment.amount_adult, 3) if is_employee_discount else 0
        child_disc = min(payment.amount_child, max(0, remaining_disc))
        child_full = payment.amount_child - child_disc

        if child_disc > 0:
            price_disc = int(child_price_tiins * payment.hours * 0.5)
            goods.append({
                "calcItemAttributeCode": 1,
                "name": f"Билет детский × {child_disc} чел. × {payment.hours} ч | Скидка 50% (сотрудник + 2 гостя)",
                "price": price_disc,
                "quantity": child_disc,
                "unit": "шт.",
                "st": 0, "vat": 0, "sgtin": None
            })

        if child_full > 0:
            price_full = child_price_tiins * payment.hours
            goods.append({
                "calcItemAttributeCode": 1,
                "name": f"Билет детский × {child_full} чел. × {payment.hours} ч",
                "price": price_full,
                "quantity": child_full,
                "unit": "шт.",
                "st": 0, "vat": 0, "sgtin": None
            })

    # === ДОП.УСЛУГИ ===
    if payment.skate_rental > 0:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Прокат коньков × {payment.skate_rental}",
            "price": skate_price_tiins,
            "quantity": payment.skate_rental,
            "unit": "шт.",
            "st": 0, "vat": 0, "sgtin": None
        })

    if payment.instructor_service:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": "Услуга инструктора",
            "price": instructor_price_tiins,
            "quantity": 1,
            "unit": "шт.",
            "st": 0, "vat": 0, "sgtin": None
        })

    # === СОХРАНЯЕМ % ДЛЯ ФРОНТА ===
    payment.percent = 50 if is_employee_discount else 0
    payment.save(update_fields=['percent'])

    # === PAYLOAD — ТАЛОН № ТОЛЬКО КАК ТЕКСТ СВЕРХУ ===
    payload = {
        "fiscal_number": EKASSA_FISCAL_NUMBER,
        "txt": True,
        "cash": False,
        "operation": "INCOME",
        "received": int(payment.total_amount * 100),
        "goods": goods,
        "company": {
            "inn": "0000000000022030",
            "sno": "osn"
        },
        "description": f"Талон № {payment.ticket_number or '—'}\n"
    }

    if payment.user.email:
        payload["customerContact"] = payment.user.email

    token = _get_token()
    if not token:
        return {"success": False, "error": "Auth failed"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        resp = _requests_session.post(
            f"{EKASSA_HOST}/api/v2/receipt",
            json=payload,
            headers=headers,
            timeout=15
        )
        result = resp.json()

        if resp.status_code == 200 and result.get("status") == "Success":
            data = result.get("data", {})
            payment.fiscalized = True
            payment.fiscal_uuid = data.get("id")
            payment.fiscal_link = data.get("link", "")
            payment.save(update_fields=['fiscalized', 'fiscal_uuid', 'fiscal_link'])
            return {"success": True, "fiscal_id": data.get("id"), "fiscal_link": data.get("link")}

        else:
            error_msg = str(result).lower()
            if "shift must be closed" in error_msg or "смена" in error_msg:
                close_shift()
                open_shift()
                return fiscalize_payment(payment)
            return {"success": False, "error": result.get("message", "Unknown error")}

    except Exception as e:
        return {"success": False, "error": str(e)}
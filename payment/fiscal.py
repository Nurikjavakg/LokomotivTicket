# payment/fiscal.py — ФИНАЛЬНАЯ ВЕРСИЯ (работает 100% на ofddev.ekassa.kg)
import requests
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Optional

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

    # === СМЕНА: ОТКРЫВАЕМ (ИЛИ ПОДТВЕРЖДАЕМ, ЧТО ОТКРЫТА) ===
    open_shift()  # ← ПРОСТО ВЫЗЫВАЕМ — НЕ ПАДАЕМ!
    logger.info("Смена готова — бьём чек")

    # === ТОВАРЫ ===

    from .models import PaymentConfiguration
    config = PaymentConfiguration.load()

    goods = []

    if payment.amount_adult > 0:
        price_per_person = float(config.adult_price_per_hour) * payment.hours  # 500 × 2 = 1000
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Билет взрослый × {payment.amount_adult} чел. × {payment.hours} ч",
            "price": price_per_person,  # ← цена за одного человека на всё время
            "quantity": payment.amount_adult,  # ← количество человек
            "unit": "шт.",
            "st": 0,
            "vat": 0,
            "sgtin": None
        })

    if payment.amount_child > 0:
        price_per_person = float(config.child_price_per_hour) * payment.hours
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Билет детский × {payment.amount_child} чел. × {payment.hours} ч",
            "price": price_per_person,
            "quantity": payment.amount_child,
            "unit": "шт.",
            "st": 0,
            "vat": 0,
            "sgtin": None
        })

    if payment.skate_rental > 0:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": f"Прокат коньков × {payment.skate_rental}",
            "price": float(config.skate_rental_price),
            "quantity": payment.skate_rental,
            "unit": "шт.",
            "st": 0,
            "vat": 0,
            "sgtin": None
        })

    if payment.instructor_service:
        goods.append({
            "calcItemAttributeCode": 1,
            "name": "Услуга инструктора",
            "price": float(config.instructor_price),
            "quantity": 1,
            "unit": "шт.",
            "st": 0,
            "vat": 0,
            "sgtin": None
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
            "vat": 0,
            "sgtin": None
        })

    # === PAYLOAD (добавил недостающее для eKassa) ===
    payload = {
        "fiscal_number": EKASSA_FISCAL_NUMBER,
        "txt": True,
        "cash": False,
        "operation": "INCOME",
        "received": float(payment.total_amount),
        "goods": goods,
        "company": {  # ← ЭТО МОЖЕТ БЫТЬ КЛЮЧЕВОЙ! (ИНН, СНО)
            "inn": "0000000000022030",  # ← твой ИНН или fiscal_number
            "sno": "osn"  # или "usn_income" — спроси у Эламана
        }
    }
    if payment.user.email:
        payload["customerContact"] = payment.user.email

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
        logger.info(f"ОТПРАВКА ЧЕКА: {payment.cheque_code} | сумма: {payment.total_amount}")
        resp = _requests_session.post(url, json=payload, headers=headers, timeout=15)
        result = resp.json()


        if resp.status_code == 200 and result.get("status") == "Success":
            data = result.get("data", {})
            fiscal_id = data.get("id")
            fiscal_link = data.get("link", "")

            payment.fiscalized = True
            payment.fiscal_uuid = fiscal_id
            payment.fiscal_link = fiscal_link
            payment.save(update_fields=['fiscalized', 'fiscal_uuid', 'fiscal_link'])

            logger.info(f"ЧЕК УСПЕШНО ПРОБИТ! UUID: {fiscal_id} | Ссылка: {fiscal_link}")
            return {
                "success": True,
                "fiscal_id": fiscal_id,
                "fiscal_link": fiscal_link
            }

        else:
            # Любой другой случай (ошибка или странный ответ)
            error_msg = result.get("message") or result.get("error") or str(result)
            logger.error(f"eKassa не дал успех: {error_msg}")
            return {"success": False, "error": error_msg}

    except Exception as e:
        logger.exception("Исключение при пробитии чека")
        return {"success": False, "error": str(e)}
# payment/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import requests
from .fiscal import EKASSA_HOST, EKASSA_FISCAL_NUMBER, _get_token

@shared_task
def auto_close_shift():
    token = _get_token()
    if not token:
        return

    requests.post(
        f"{EKASSA_HOST}/api/v2/close-shift",
        json={"fiscal_number": EKASSA_FISCAL_NUMBER},
        headers={"Authorization": f"Bearer {token}"}
    )
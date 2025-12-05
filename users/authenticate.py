
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    """
    Поддерживает авторизацию:
    • из заголовка Authorization: Bearer ...
    • из cookie 'access_token'
    """
    def authenticate(self, request):
        # 1. Сначала пробуем из cookie
        raw_token = request.COOKIES.get('access_token')

        # 2. если нет — из заголовка (чтобы старый код не ломался)
        if raw_token is None:
            header = self.get_header(request)
            if header is not None:
                raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)


            self.enforce_csrf(request)

            return (user, validated_token)
        except Exception:
            return None

    def enforce_csrf(self, request):
        check = CSRFCheck()

        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


def _flatten_fields(detail) -> dict:
    if isinstance(detail, dict):
        out = {}
        for key, value in detail.items():
            if isinstance(value, list):
                out[key] = [str(item) for item in value]
            elif isinstance(value, dict):
                out[key] = [str(value)]
            else:
                out[key] = [str(value)]
        return out
    if isinstance(detail, list):
        return {"non_field_errors": [str(item) for item in detail]}
    return {"non_field_errors": [str(detail)]}


def poisker_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = "error"
    message = "Ошибка запроса"
    fields = {}

    if isinstance(exc, ValidationError):
        code = "validation_error"
        message = "Проверьте введённые данные"
        fields = _flatten_fields(exc.detail)
    elif hasattr(exc, "default_code"):
        code = getattr(exc, "default_code", code)
        if isinstance(exc.detail, (list, dict)):
            if isinstance(exc.detail, dict) and "detail" not in exc.detail:
                fields = _flatten_fields(exc.detail)
                message = "Проверьте введённые данные"
            else:
                message = str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail)
        else:
            message = str(exc.detail)
    elif isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "authentication_failed"
        message = message or "Требуется авторизация"
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        code = "permission_denied"
        message = message or "Недостаточно прав"
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
        message = message or "Не найдено"
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        code = "rate_limited"
        message = message or "Слишком много запросов"

    payload = {"code": code, "message": message}
    if fields:
        payload["fields"] = fields
    response.data = payload
    return response


class ServiceValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_detail = "Проверьте введённые данные"

    def __init__(self, message: str):
        super().__init__(detail={"non_field_errors": [message]})

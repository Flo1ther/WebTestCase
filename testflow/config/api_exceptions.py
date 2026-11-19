from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    detail = response.data
    message = detail.get("detail") if isinstance(detail, dict) else None
    if not message:
        message = "Помилка перевірки запиту." if response.status_code == 400 else "Не вдалося завершити запит."
    response.data = {"error": {"code": getattr(exc, "default_code", f"http_{response.status_code}"), "message": str(message), "details": detail}}
    return response

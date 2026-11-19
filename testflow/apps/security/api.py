from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import exception_handler as default_handler
from rest_framework.response import Response

def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError): return Response({'detail': exc.messages}, status=400)
    response = default_handler(exc, context)
    if response is not None:
        response.data = {'errors': response.data, 'message': 'Запит відхилено. Перевірте введені дані.'}
    return response

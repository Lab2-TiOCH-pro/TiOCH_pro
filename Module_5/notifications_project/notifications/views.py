from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError

from .services.dispatcher import NotificationDispatcher
from .schemas import NotificationSchema

class NotificationAPIView(APIView):
    def post(self, request):
        try:
            data = NotificationSchema.validate(request.data)
            
            content = self._prepare_content(data)

            results = {}
            if data['email']:
                results['email'] = NotificationDispatcher.send_email(
                    data['email'], data['subject'], content
                )
            if data['slack_recipient']:
                results['slack'] = NotificationDispatcher.send_slack(
                    data['slack_recipient'], content
                )

            return Response({
                'status': 'success',
                'results': results
            }, status=status.HTTP_200_OK)

        except (serializers.ValidationError, DjangoValidationError) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': "Wystąpił błąd podczas wysyłania powiadomienia",
                'debug': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _prepare_content(self, data):
        return f"{data['message']}\n\n{data['details']}" if data['details'] else data['message']
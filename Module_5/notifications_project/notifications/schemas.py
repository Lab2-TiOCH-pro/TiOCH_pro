from rest_framework import serializers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

class NotificationSchema:
    @staticmethod
    def validate(data: dict) -> dict:
        try:
            if not data.get('email') and not data.get('slack_recipient'):
                raise serializers.ValidationError(
                    "Podaj email lub odbiorcę Slack (@user/#channel)"
                )

            if data.get('email'):
                validate_email(data['email'])

            return {
                'email': data.get('email'),
                'slack_recipient': data.get('slack_recipient'),
                'subject': data.get('subject', 'Notification'),
                'message': data.get('message', ''),
                'details': data.get('details', '')
            }
            
        except DjangoValidationError as e:
            raise serializers.ValidationError(f"Nieprawidłowy email: {str(e)}")
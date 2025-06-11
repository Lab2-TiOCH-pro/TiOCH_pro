from .email import EmailService
from .slack import SlackService

class NotificationDispatcher:
    @staticmethod
    def send_email(to: str, subject: str, content: str) -> dict:
        return EmailService.send(to, subject, content)

    @staticmethod
    def send_slack(recipient: str, content: str) -> dict:
        return SlackService().send_message(recipient, content)
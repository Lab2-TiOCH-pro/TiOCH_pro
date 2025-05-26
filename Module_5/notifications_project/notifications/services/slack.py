from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from django.conf import settings

class SlackService:
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_TOKEN)

    def send_message(self, recipient: str, content: str) -> dict:
        if recipient.startswith('@'):
            return self._send_dm(recipient[1:], content)
        return self._send_channel_message(recipient, content)

    def _send_dm(self, username: str, content: str) -> dict:
        user = self._find_user(username)
        if not user:
            raise ValueError(f"User @{username} not found")
        
        conv = self.client.conversations_open(users=[user['id']])
        return self._post_message(conv["channel"]["id"], content)

    def _send_channel_message(self, channel: str, content: str) -> dict:
        return self._post_message(channel, content)

    def _post_message(self, channel_id: str, content: str) -> dict:
        response = self.client.chat_postMessage(
            channel=channel_id,
            text=content,
            username="Notification Bot",
            icon_emoji=":bell:"
        )
        return {'status': 'success', 'channel': channel_id, 'ts': response['ts']}

    def _find_user(self, name: str):
        try:
            response = self.client.users_list()
            return next((u for u in response['members'] if not u['deleted'] and 
                       (u['name'] == name or 
                        u.get('real_name', '').lower() == name.lower() or
                        u.get('profile', {}).get('display_name', '').lower() == name.lower())), None)
        except SlackApiError:
            return None
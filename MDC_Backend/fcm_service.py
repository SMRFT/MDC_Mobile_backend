import logging
try:
    from .expo_push_service import send_expo_push
except ImportError:
    from MDC_Backend.expo_push_service import send_expo_push

logger = logging.getLogger(__name__)

def send_fcm_push(fcm_token: str, title: str, body: str, data: dict = None):
    """
    Backwards-compatible wrapper that dispatches push notifications via Expo Push Notification service.
    Accepts Expo Push Tokens (ExponentPushToken[...]) as well as legacy device tokens.
    """
    return send_expo_push(push_token=fcm_token, title=title, body=body, data=data)

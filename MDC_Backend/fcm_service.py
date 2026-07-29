import os
import json
import logging
import datetime
import firebase_admin
from firebase_admin import credentials, messaging


logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initializes Firebase Admin SDK from environment variables or service account file."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # 1. Try environment variables first
    project_id = os.environ.get("FIREBASE_PROJECT_ID")
    private_key = os.environ.get("FIREBASE_PRIVATE_KEY")
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")

    if project_id and private_key and client_email:
        # Format escaped newlines in private key if loaded from env string
        formatted_private_key = private_key.replace("\\n", "\n")
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": formatted_private_key,
            "client_email": client_email,
            "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email.replace('@', '%40')}"
        }
        cred = credentials.Certificate(cred_dict)
        app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized via environment credentials.")
        return app

    # 2. Try JSON credential file if present in backend directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "milestone-salem-1555f-firebase-adminsdk-fbsvc-8a0f1a193c.json")
    if os.path.exists(json_path):
        cred = credentials.Certificate(json_path)
        app = firebase_admin.initialize_app(cred)
        logger.info(f"Firebase Admin SDK initialized via JSON file: {json_path}")
        return app

    logger.warning("Firebase credentials not found. Push notifications will be simulated.")
    return None

def send_fcm_push(fcm_token: str, title: str, body: str, data: dict = None):
    """
    Sends high-priority FCM Push Notification to a target device token.
    Works even when the app is closed, killed, or in background.
    """
    if not fcm_token:
        return False, "No FCM token provided"

    try:
        app = initialize_firebase()
        if not app:
            logger.warning(f"Simulating push notification send to {fcm_token[:10]}...")
            return True, "Simulated (Firebase not configured)"

        # Prepare string-only data dict for FCM
        string_data = {}
        if data:
            for k, v in data.items():
                string_data[str(k)] = str(v) if v is not None else ""

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body or "",
            ),
            data=string_data,
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority="high",
                ttl=datetime.timedelta(days=7),
                notification=messaging.AndroidNotification(
                    channel_id="default",
                    priority="high",
                    sound="default",
                    default_sound=True,
                    default_vibrate_timings=True,
                    visibility="public"
                )
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body or ""
                        ),
                        sound="default",
                        badge=1,
                        content_available=True
                    )
                )
            )
        )

        response = messaging.send(message)
        logger.info(f"Successfully sent FCM push message: {response}")
        return True, response

    except Exception as e:
        logger.error(f"Error sending FCM push notification: {str(e)}")
        return False, str(e)


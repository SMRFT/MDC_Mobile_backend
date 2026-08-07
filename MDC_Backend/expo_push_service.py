import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_expo_push(push_token: str, title: str, body: str, data: dict = None):
    """
    Sends a high-priority push notification via Expo Push Notification service.
    Works with Expo Push Tokens formatted like 'ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]' or 'ExpoPushToken[...]'.
    """
    if not push_token:
        return False, "No push token provided"

    # If it's a dev simulated token or empty token, log and return simulation success
    if push_token.startswith("FCM_DEV_TOKEN_") or push_token == "NO_TOKEN":
        logger.info(f"Simulated Expo push notification send to {push_token}")
        return True, "Simulated (Dev Token)"

    payload = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body or "",
        "priority": "high",
        "data": data or {},
    }

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(EXPO_PUSH_URL, json=payload, headers=headers, timeout=10)
        res_json = response.json()

        if response.status_code == 200 and "data" in res_json:
            status_data = res_json.get("data", {})
            if isinstance(status_data, list) and len(status_data) > 0:
                first_item = status_data[0]
                if first_item.get("status") == "ok":
                    ticket_id = first_item.get("id", "ok")
                    logger.info(f"Successfully sent Expo push notification to {push_token[:15]}... Ticket: {ticket_id}")
                    return True, ticket_id
                else:
                    err_msg = first_item.get("message") or first_item.get("details", {})
                    logger.error(f"Expo push error for {push_token}: {err_msg}")
                    return False, str(err_msg)
            elif isinstance(status_data, dict) and status_data.get("status") == "ok":
                ticket_id = status_data.get("id", "ok")
                return True, ticket_id

        logger.error(f"Failed Expo push send HTTP {response.status_code}: {res_json}")
        return False, json.dumps(res_json)

    except Exception as e:
        logger.error(f"Exception sending Expo push notification: {str(e)}")
        return False, str(e)

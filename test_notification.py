import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MDC_Mobile_backend.settings')
django.setup()

from MDC_Backend.models import Notification, appusers
from rest_framework.test import APIClient

client = APIClient()

# 1. Register Token
appusers.objects.filter(reg_no='MDC/001/2025').delete()
user = appusers.objects.create(reg_no='MDC/001/2025', mobile_number='9999999999', password='pass')

res1 = client.post('/api/register-fcm-token/', {'reg_no': 'MDC/001/2025', 'fcm_token': 'dummy_fcm_token_12345'}, format='json')
print('Register Token Status:', res1.status_code, res1.data)

# 2. Create Notification
noti_payload = {
    'created_by': 'Admin',
    'title': 'test',
    'sub': 'testing',
    'members': [
        {
            'reg_no': 'MDC/001/2025',
            'name': 'K.Dhuvaraga varshini',
            'is_send': False,
            'is_read': False,
            'sent_datetime': None,
            'read_datetime': None
        }
    ]
}

res2 = client.post('/api/notifications/', noti_payload, format='json')
print('Create Notification Status:', res2.status_code, res2.data)

noti_id = res2.data.get('notification_id')

# 3. Mark Notification Read
res3 = client.post('/api/notifications/mark-read/', {'notification_id': noti_id, 'reg_no': 'MDC/001/2025'}, format='json')
print('Mark Read Status:', res3.status_code, res3.data)

# 4. User Notification List
res4 = client.get('/api/notifications/user/MDC/001/2025/')
print('User Notifications Count:', len(res4.data), 'Data:', res4.data)

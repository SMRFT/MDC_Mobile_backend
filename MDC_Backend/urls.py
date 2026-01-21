from django.urls import path
from .views import PatientList, PatientDetail, PatientSearchView

urlpatterns = [
    path('patients/', PatientList.as_view(), name='patient-list'),
    path('patients/<int:pk>/', PatientDetail.as_view(), name='patient-detail'),
    path('search/', PatientSearchView.as_view(), name='patient-search'),
]

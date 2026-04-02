from django.urls import path
from .views import PatientList, PatientDetail, PatientSearchView, GoalsAssessmentView, GoalsAssessmentDetailView, FileUploadView, FileDownloadView, FileDeleteView, LeaveFormView

urlpatterns = [
    path('patients/', PatientList.as_view(), name='patient-list'),
    path('patients/<int:pk>/', PatientDetail.as_view(), name='patient-detail'),
    path('search/', PatientSearchView.as_view(), name='patient-search'),
    path('goals/', GoalsAssessmentView.as_view(), name='goals-list-create'),
    path('goals/update/<str:pk>/', GoalsAssessmentDetailView.as_view(), name='goals-update'),
    path('leave/', LeaveFormView.as_view(), name='leave-form'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('file/<str:file_id>/', FileDownloadView.as_view(), name='file-download'),
    path('file/delete/<str:file_id>/', FileDeleteView.as_view(), name='file-delete'),
]

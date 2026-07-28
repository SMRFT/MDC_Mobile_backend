from django.urls import path
try:
    from .views import PatientList, PatientDetail, PatientSearchView, PatientPhoneSearchView, RegisterUserView, ChangePasswordView, DeactivateAccountView, GoalsAssessmentView, GoalsAssessmentDetailView, FileUploadView, FileDownloadView, FileDeleteView, LeaveFormView, DevelopmentGoalsView, DevelopmentGoalsDetailView, HistoryRecordingSheetView, AssessmentReportView, PatientSessionAttendanceView, ConfirmSessionAttendanceView
    from .reportDownloader import HistorySheetPDFView, AssessmentReportPDFView
except ImportError:
    from MDC_Backend.views import PatientList, PatientDetail, PatientSearchView, PatientPhoneSearchView, RegisterUserView, ChangePasswordView, DeactivateAccountView, GoalsAssessmentView, GoalsAssessmentDetailView, FileUploadView, FileDownloadView, FileDeleteView, LeaveFormView, DevelopmentGoalsView, DevelopmentGoalsDetailView, HistoryRecordingSheetView, AssessmentReportView, PatientSessionAttendanceView, ConfirmSessionAttendanceView
    from MDC_Backend.reportDownloader import HistorySheetPDFView, AssessmentReportPDFView

urlpatterns = [
    path('patients/', PatientList.as_view(), name='patient-list'),
    path('patients/<int:pk>/', PatientDetail.as_view(), name='patient-detail'),
    path('search/', PatientSearchView.as_view(), name='patient-search'),
    path('search-phone/', PatientPhoneSearchView.as_view(), name='patient-search-phone'),
    path('register-user/', RegisterUserView.as_view(), name='register-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('deactivate-account/', DeactivateAccountView.as_view(), name='deactivate-account'),
    path('goals/', GoalsAssessmentView.as_view(), name='goals-list-create'),
    path('goals/update/<str:pk>/', GoalsAssessmentDetailView.as_view(), name='goals-update'),
    path('developmental-goals/', DevelopmentGoalsView.as_view(), name='developmental-goals-list-create'),
    path('developmental-goals/<str:pk>/', DevelopmentGoalsDetailView.as_view(), name='developmental-goals-detail'),
    path('leave/', LeaveFormView.as_view(), name='leave-form'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('file/<str:file_id>/', FileDownloadView.as_view(), name='file-download'),
    path('file/delete/<str:file_id>/', FileDeleteView.as_view(), name='file-delete'),
    path('history-sheet/', HistoryRecordingSheetView.as_view(), name='history-sheet'),
    path('history-sheet/pdf/', HistorySheetPDFView.as_view(), name='history-sheet-pdf'),
    path('assessment-report/pdf/', AssessmentReportPDFView.as_view(), name='assessment-report-pdf'),
    path('assessment-report/', AssessmentReportView.as_view(), name='assessment-report'),
    path('patient-session-attendance/', PatientSessionAttendanceView.as_view(), name='patient-session-attendance'),
    path('patient-session-attendance/confirm/<str:pk>/', ConfirmSessionAttendanceView.as_view(), name='patient-session-attendance-confirm'),
]

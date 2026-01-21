from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Registration, PatientAttendance
from .serializers import RegistrationSerializer, PatientAttendanceSerializer

class PatientList(generics.ListCreateAPIView):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer

class PatientDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer

class PatientSearchView(APIView):
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            registration = Registration.objects.get(registration_number=reg_no)
            attendance = PatientAttendance.objects.filter(registration_number=reg_no).order_by('-attendance_date')
            
            reg_data = RegistrationSerializer(registration).data
            att_data = PatientAttendanceSerializer(attendance, many=True).data
            
            return Response({
                "registration": reg_data,
                "attendance": att_data
            })
        except Registration.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

from rest_framework import serializers
from .models import Registration, PatientAttendance

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = '__all__'

class PatientAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAttendance
        fields = '__all__'

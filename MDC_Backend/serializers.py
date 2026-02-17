from rest_framework import serializers
from .models import Registration, PatientAttendance, GoalsAssessment
import json

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = '__all__'

class PatientAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAttendance
        fields = '__all__'


class CleanJSONField(serializers.JSONField):
    """Custom JSONField that converts OrderedDicts to regular dicts before validation"""
    
    def to_internal_value(self, data):
        # Recursively convert OrderedDicts to dicts
        def convert(obj):
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            return obj
        
        cleaned_data = convert(data)
        return super().to_internal_value(cleaned_data)
    
    def to_representation(self, value):
        # Also clean when reading from database
        def convert(obj):
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            return obj
        
        return convert(value)

class GoalsAssessmentSerializer(serializers.ModelSerializer):
    # Override JSONFields to use custom field that handles OrderedDicts
    goals = CleanJSONField(required=False)
    goalsphoto = CleanJSONField(required=False)
    goalsvideo = CleanJSONField(required=False)
    
    class Meta:
        model = GoalsAssessment
        fields = '__all__'

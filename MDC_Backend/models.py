from djongo import models
from djongo.models import ObjectIdField
from django.db import transaction

class AuditModel(models.Model):
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    lastmodified_by = models.CharField(max_length=100, blank=True, null=True)
    lastmodified_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

class Registration(models.Model):
    name_of_child = models.CharField(max_length=200)
    dob = models.DateTimeField(null=True, blank=True)
    age = models.TextField(null=True, blank=True) # JSON string
    sex = models.CharField(max_length=20, null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    mother_name = models.CharField(max_length=200, null=True, blank=True)
    father_name = models.CharField(max_length=200, null=True, blank=True)
    guardian_name = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    mail_id = models.EmailField(null=True, blank=True)
    mother_phone_number = models.CharField(max_length=20, null=True, blank=True)
    father_phone_number = models.CharField(max_length=20, null=True, blank=True)
    reason_for_visit = models.TextField(null=True, blank=True) # JSON string
    duration_of_symptoms = models.CharField(max_length=200, null=True, blank=True)
    previous_treatment_done = models.CharField(max_length=200, null=True, blank=True)
    source_of_referral = models.TextField(null=True, blank=True) # JSON string
    registration_number = models.CharField(max_length=100, unique=True)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'milestone_backend_registration'

    def __str__(self):
        return f"{self.name_of_child} ({self.registration_number})"

class PatientAttendance(models.Model):
    registration_number = models.CharField(max_length=100)
    attendance_date = models.DateTimeField(null=True, blank=True)
    session = models.IntegerField(default=0)
    therapy_details = models.TextField(null=True, blank=True) # JSON string
    therapy_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bill_details = models.TextField(null=True, blank=True) # JSON string
    consultant_doctor = models.TextField(null=True, blank=True) # JSON string
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'milestone_backend_patientattendance'

    def __str__(self):
        return f"Attendance for {self.registration_number} on {self.attendance_date}"

class GoalsAssessment(AuditModel):   
    _id = models.ObjectIdField(primary_key=True)

    registration_number = models.CharField(max_length=50)
    date = models.DateField()
    deadline = models.DateField()
    goals = models.JSONField(default=list, blank=True)
    parent_comments = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    refference = models.CharField(max_length=500,blank=True, null=True)
    goalsphoto = models.JSONField(default=list, blank=True)
    goalsvideo = models.JSONField(default=list, blank=True)
    
    class Meta:
        unique_together = ('registration_number', 'date')
        db_table = 'milestone_backend_goalsassessment'
    def __str__(self):
        return f"{self.registration_number} - {self.date}"
    
class leaveform(AuditModel):
    registration_number = models.CharField(max_length=50)
    leave_date = models.DateField()
    leave_reason = models.TextField(blank=True, null=True)
    leave_status = models.CharField(max_length=50,default="Pending")
    leave_approved_by = models.CharField(max_length=50,null=True, blank=True)
    leave_approved_date = models.DateField(null=True, blank=True)
    leave_reject_comments = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('registration_number', 'leave_date')
        db_table = 'milestone_backend_leaveform'
    def __str__(self):
        return f"{self.registration_number} - {self.leave_date}"
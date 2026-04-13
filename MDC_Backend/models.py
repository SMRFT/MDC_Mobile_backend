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

class appusers(AuditModel):
    reg_no = models.CharField(max_length=100,primary_key=True)
    mobile_number = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=100)
    previous_password = models.CharField(max_length=100,null=True, blank=True)
    
    class Meta:
        db_table = 'milestone_backend_appusers'
    def __str__(self):
        return self.reg_no


class DevelopmentGoals(AuditModel):
    _id = models.ObjectIdField(primary_key=True)
    registration_number = models.CharField(max_length=50)
    date = models.DateField()
    development_goals = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'milestone_backend_developmentgoals'

    def __str__(self):
        return f"{self.registration_number} - {self.date}"

class TherapyDetails(AuditModel):
    _id = models.ObjectIdField()
    therapy_name = models.CharField(max_length=255)
    
    class Meta:
        db_table = "milestone_backend_therapydetails"

class GoalDomain(AuditModel):
    _id = models.ObjectIdField(primary_key=True)
    name = models.CharField(max_length=200)
    therapy_type = models.CharField(max_length=100) # Storing ID of TherapyDetails as string
    domain_no = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'milestone_backend_goaldomain'
    
    def save(self, *args, **kwargs):
        if not self.domain_no:
            try:
                from bson import ObjectId
                therapy = TherapyDetails.objects.get(_id=ObjectId(self.therapy_type))
                prefix = therapy.therapy_name[:2].upper()
            except:
                prefix = "GN"
                
            count = GoalDomain.objects.filter(therapy_type=self.therapy_type).count()
            self.domain_no = f"D-{prefix}-{count+1:03}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name

class GoalLevel(AuditModel):
    _id = models.ObjectIdField(primary_key=True)
    name = models.CharField(max_length=50) 

    class Meta:
        db_table = 'milestone_backend_goallevel'

    def __str__(self): return self.name

class GoalLibrary(AuditModel):
    _id = models.ObjectIdField(primary_key=True)
    goal_name = models.TextField()
    goal_no = models.CharField(max_length=20, blank=True)
    domain = models.CharField(max_length=100) # Storing ID as string
    therapy_type = models.CharField(max_length=100) # Storing ID as string
    level = models.CharField(max_length=100, blank=True, null=True) # Storing ID as string

    class Meta:
        db_table = 'milestone_backend_goallibrary'
    
    def save(self, *args, **kwargs):
        if not self.goal_no:
            prefix = "G"
            try:
                from bson import ObjectId
                # Try lookup by ObjectId first (backward compatibility)
                if len(self.domain) == 24: 
                    domain_obj = GoalDomain.objects.get(_id=ObjectId(self.domain))
                    prefix = domain_obj.domain_no
                else: 
                    # Use domain_no directly if it was saved as name/no
                    prefix = self.domain
            except:
                prefix = self.domain or "G"
                
            count = GoalLibrary.objects.filter(domain=self.domain).count()
            # Clean prefix if it contains spaces or special characters
            prefix_clean = str(prefix).split('(')[0].strip()
            self.goal_no = f"G-{prefix_clean}-{count+1:03}"
        super().save(*args, **kwargs)

    def __str__(self): return self.goal_name


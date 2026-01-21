from django.db import models

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

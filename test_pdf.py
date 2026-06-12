import os
import sys

# Add current path to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock Django setup
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MDC_Mobile_backend.settings')
django.setup()

from MDC_Backend.reportDownloader import build_report_html, build_assessment_report_html
from xhtml2pdf import pisa

record = {
    "registration_number": "MDC/212/2026",
    "identification_data": {
        "name": "Test Child",
        "dob": "2020-01-01",
        "date_of_assessment": "2026-06-08"
    },
    "demographic_data": {
        "father": "Father Name",
        "mother": "Mother Name"
    },
    "created_by": "some_id" # This will trigger signature lookup or we can mock it
}

# Let's mock _get_creator_signature to return Ms. Sivashankari signature
import MDC_Backend.reportDownloader as rd
rd._get_creator_signature = lambda x: "<strong>Ms. Sivashankari,</strong><br/>M.sc Clinical Psychology, B.sc PJCS<br/>Psychologist"

html_content = build_report_html(record)

with open("test_out.html", "w", encoding="utf-8") as f:
    f.write(html_content)

with open("test_out.pdf", "wb") as f:
    pisa.CreatePDF(html_content, dest=f)

# Mock assessment documents
physio = {"on_observation": '{"restingPosture":"Normal"}', "tone": '{"upperLimb":"Normal"}'}
pediatric = {}
analysis = {"provisional_diagnosis": "Patient presents with clinical features Suggestive...", "preferred_language": '{"tamil":true}', "mapping_therapy": '{"PSY":{"BT/CT":true}}'}
language = {}
psychology = {"behaviour_problems": '["Temper Tantrums"]', "general_temperament": '{"activitylevel":"clinical"}', "assessments_used": '{"dst": {"da": "clinical", "dq": "clinical"}, "otherAssessments": [{"key": "clinical(key)", "value": "clinical(value)"}]}'}
registration = {"name_of_child": "Test Child", "dob": "2020-01-01", "father": "Father Name", "mother": "Mother Name"}

assess_html = build_assessment_report_html(
    reg_no="MDC/212/2026",
    physio=physio,
    pediatric=pediatric,
    analysis=analysis,
    language=language,
    psychology=psychology,
    registration=registration
)

with open("test_assessment_out.html", "w", encoding="utf-8") as f:
    f.write(assess_html)

with open("test_assessment_out.pdf", "wb") as f:
    pisa.CreatePDF(assess_html, dest=f)

print("PDF and HTML generated successfully.")

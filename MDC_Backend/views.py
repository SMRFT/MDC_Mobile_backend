import os
import sys
import re
import shutil

import tempfile
import traceback
import gridfs
import certifi
from datetime import datetime
from django.utils import timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv


from django.conf import settings
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from pymongo import MongoClient

try:
    from .models import Registration, PatientAttendance, appusers, GoalsAssessment, leaveform, DevelopmentGoals, Notification
except ImportError:
    from MDC_Backend.models import Registration, PatientAttendance, appusers, GoalsAssessment, leaveform, DevelopmentGoals, Notification

try:
    from .serializers import (
        RegistrationSerializer, PatientAttendanceSerializer,
        GoalsAssessmentSerializer, LeaveFormSerializer, DevelopmentGoalsSerializer, NotificationSerializer
    )
except ImportError:
    from MDC_Backend.serializers import (
        RegistrationSerializer, PatientAttendanceSerializer,
        GoalsAssessmentSerializer, LeaveFormSerializer, DevelopmentGoalsSerializer, NotificationSerializer
    )

try:
    from .fcm_service import send_fcm_push
except ImportError:
    try:
        from MDC_Backend.fcm_service import send_fcm_push
    except ImportError:
        send_fcm_push = None


try:
    from .utils import compress_video
except ImportError:
    try:
        from MDC_Backend.utils import compress_video
    except ImportError:
        compress_video = None

try:
    from .reportDownloader import clean_record
except ImportError:
    try:
        from MDC_Backend.reportDownloader import clean_record
    except ImportError:
        clean_record = None

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

class PatientPhoneSearchView(APIView):
    def get(self, request):
        phone = request.query_params.get('phone')
        password = request.query_params.get('password')
        
        if not phone or not password:
            return Response({"error": "Phone number and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate against appusers
        matched_users = list(appusers.objects.filter(mobile_number=phone, password=password))
        matched_users = [user for user in matched_users if user.is_active]
        
        if not matched_users:
            return Response({"error": "Invalid credentials. Please check your mobile number and password."}, status=status.HTTP_401_UNAUTHORIZED)
            
        data = []
        for user in matched_users:
            try:
                reg = Registration.objects.get(registration_number=user.reg_no)
                data.append({
                    "id": str(user.reg_no),
                    "name": reg.name_of_child,
                    "registration_number": reg.registration_number
                })
            except Registration.DoesNotExist:
                data.append({
                    "id": str(user.reg_no),
                    "name": "Child Record Missing",
                    "registration_number": user.reg_no
                })
            
        return Response(data)

class RegisterUserView(APIView):
    def post(self, request):
        reg_no = request.data.get('reg_no')
        mobile = request.data.get('mobile')
        email = request.data.get('email', '')
        password = request.data.get('password')
        
        if not reg_no or not mobile or not password:
            return Response({"error": "Registration Number, Mobile, and Password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure the user doesn't already exist
        if appusers.objects.filter(reg_no=reg_no).exists():
            return Response({"error": "This Registration Number is already registered."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create the appuser record
            name = request.data.get('name') # Optional but good to pass
            app_user = appusers.objects.create(
                reg_no=reg_no,
                mobile_number=mobile,
                email=email,
                password=password
            )
            return Response({"message": "User registered successfully", "reg_no": app_user.reg_no}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChangePasswordView(APIView):
    def post(self, request):
        mobile = request.data.get('mobile')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not mobile or not old_password or not new_password:
            return Response({"error": "Mobile, Old Password, and New Password are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = appusers.objects.get(mobile_number=mobile, password=old_password)
            user.password = new_password
            user.save()
            return Response({"message": "Password changed successfully"})
        except appusers.DoesNotExist:
            return Response({"error": "Invalid current credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeactivateAccountView(APIView):
    def post(self, request):
        reg_no = request.data.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration Number is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = appusers.objects.get(reg_no=reg_no)
            user.is_active = False
            user.save()
            return Response({"message": "Account deactivated successfully"}, status=status.HTTP_200_OK)
        except appusers.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LeaveFormView(APIView):
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        leaves = leaveform.objects.filter(registration_number=reg_no)
        
        if month and month != 'All':
            # month should be 1-12
            leaves = leaves.filter(leave_date__month=month)
        
        if year:
            leaves = leaves.filter(leave_date__year=year)
            
        serializer = LeaveFormSerializer(leaves.order_by('-leave_date'), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeaveFormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if not db_name:
    db_name = "Milestone"

client = MongoClient(mongo_uri)

# Initialize GridFS
try:
    db = client[str(db_name)]
    fs = gridfs.GridFS(db)
except Exception as e:
    print(f"Error connecting to MongoDB GridFS: {e}")
    fs = None

class GoalsAssessmentView(APIView):
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        goals = GoalsAssessment.objects.filter(registration_number=reg_no)
        serializer = GoalsAssessmentSerializer(goals, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = GoalsAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoalsAssessmentDetailView(APIView):
    def get_object(self, pk):
        try:
            # Convert string pk to ObjectId for djongo
            return GoalsAssessment.objects.get(pk=ObjectId(pk))
        except GoalsAssessment.DoesNotExist:
            return None

    def put(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"error": "Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get existing file IDs before update
        old_photo_ids = set()
        if goal.goalsphoto:
            for p in goal.goalsphoto:
                if isinstance(p, dict) and 'id' in p:
                    old_photo_ids.add(str(p['id']))
                elif isinstance(p, str):
                    # Extract ID from URL if possible, or handle as ID
                    old_photo_ids.add(p)

        old_video_ids = set()
        if goal.goalsvideo:
            for v in goal.goalsvideo:
                if isinstance(v, dict) and 'id' in v:
                    old_video_ids.add(str(v['id']))
                elif isinstance(v, str):
                    old_video_ids.add(v)

        serializer = GoalsAssessmentSerializer(goal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Post-save: Cleanup removed files
            new_photo_ids = set()
            new_photos = request.data.get('goalsphoto', [])
            for p in new_photos:
                if isinstance(p, dict) and 'id' in p:
                    new_photo_ids.add(str(p['id']))
                elif isinstance(p, str):
                    new_photo_ids.add(p)

            new_video_ids = set()
            new_videos = request.data.get('goalsvideo', [])
            for v in new_videos:
                if isinstance(v, dict) and 'id' in v:
                    new_video_ids.add(str(v['id']))
                elif isinstance(v, str):
                    new_video_ids.add(v)

            # Find deleted IDs
            deleted_photo_ids = old_photo_ids - new_photo_ids
            deleted_video_ids = old_video_ids - new_video_ids
            
            for fid in deleted_photo_ids | deleted_video_ids:
                try:
                    if ObjectId.is_valid(fid):
                        fs.delete(ObjectId(fid))
                        print(f"DEBUG: Deleted file {fid} from GridFS")
                except Exception as e:
                    print(f"DEBUG: Error deleting file {fid}: {e}")

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"error": "Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Cleanup all associated files
        all_file_ids = []
        if goal.goalsphoto:
            for p in goal.goalsphoto:
                if isinstance(p, dict) and 'id' in p:
                    all_file_ids.append(str(p['id']))
                elif isinstance(p, str):
                    all_file_ids.append(p)
        
        if goal.goalsvideo:
            for v in goal.goalsvideo:
                if isinstance(v, dict) and 'id' in v:
                    all_file_ids.append(str(v['id']))
                elif isinstance(v, str):
                    all_file_ids.append(v)
        
        for fid in all_file_ids:
            try:
                if ObjectId.is_valid(fid):
                    fs.delete(ObjectId(fid))
                    print(f"DEBUG: Deleted file {fid} during assessment deletion")
            except Exception as e:
                print(f"DEBUG: Error deleting file {fid} during assessment deletion: {e}")
        
        goal.delete()
        return Response({"message": "Assessment and associated media deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

def enrich_development_goals_data(data):
    try:
        therapy_map = {}
        for t in db['milestone_backend_therapydetails'].find():
            t_name = t.get('therapy_name', '')
            if 'therapy_id' in t and t['therapy_id']:
                therapy_map[str(t['therapy_id'])] = t_name
            if '_id' in t:
                therapy_map[str(t['_id'])] = t_name

        domain_map = {}
        for d in db['milestone_backend_goaldomain'].find():
            d_name = d.get('name', '')
            if 'domain_no' in d and d['domain_no']:
                domain_map[str(d['domain_no'])] = d_name
            if '_id' in d:
                domain_map[str(d['_id'])] = d_name

        level_map = {}
        for l in db['milestone_backend_goallevel'].find():
            l_name = l.get('name', '')
            if 'level_id' in l and l['level_id']:
                level_map[str(l['level_id'])] = l_name
            if '_id' in l:
                level_map[str(l['_id'])] = l_name

        is_list = isinstance(data, list)
        items = data if is_list else [data]

        for doc in items:
            if not isinstance(doc, dict):
                continue
            dev_goals = doc.get('development_goals', [])
            if isinstance(dev_goals, list):
                for g in dev_goals:
                    if isinstance(g, dict):
                        t_val = g.get('therapy', '')
                        d_val = g.get('domain', '')
                        l_val = g.get('level', '')

                        g['therapy_name'] = therapy_map.get(str(t_val), t_val)
                        g['domain_name'] = domain_map.get(str(d_val), d_val)
                        g['level_name'] = level_map.get(str(l_val), l_val)
        return data
    except Exception as e:
        print(f"Error enriching development goals: {e}")
        return data

class DevelopmentGoalsView(APIView):
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        goals = DevelopmentGoals.objects.filter(registration_number=reg_no).order_by('-date')
        serializer = DevelopmentGoalsSerializer(goals, many=True)
        data = enrich_development_goals_data(serializer.data)
        return Response(data)

    def post(self, request):
        serializer = DevelopmentGoalsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DevelopmentGoalsDetailView(APIView):
    def get_object(self, pk):
        try:
            return DevelopmentGoals.objects.get(pk=ObjectId(pk))
        except (DevelopmentGoals.DoesNotExist, Exception):
            return None

    def get(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"error": "Development Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = DevelopmentGoalsSerializer(goal)
        data = enrich_development_goals_data(serializer.data)
        return Response(data)

    def put(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"error": "Development Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = DevelopmentGoalsSerializer(goal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"error": "Development Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        goal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FileDeleteView(APIView):
    def delete(self, request, file_id):
        try:
            if not ObjectId.is_valid(file_id):
                return Response({"error": "Invalid file ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            fs.delete(ObjectId(file_id))
            return Response({"message": "File deleted successfully"}, status=status.HTTP_200_OK)
        except gridfs.errors.NoFile:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print("DEBUG: FileUploadView POST called")
        print(f"DEBUG: Content-Type: {request.content_type}")
        try:
            print(f"DEBUG: Body preview: {request.body[:200]}")
        except Exception as e:
            print(f"DEBUG: Could not print body: {e}")
            
        print(f"DEBUG: FILES keys: {request.FILES.keys()}")
        if 'file' in request.FILES:
            print(f"DEBUG: File name: {request.FILES['file'].name}")
            print(f"DEBUG: File size: {request.FILES['file'].size}")
        else:
            print("DEBUG: 'file' key not found in request.FILES")

        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_id = None
        file_url = None

        try:
            if file.content_type.startswith('video/'):
                # Save to temp file for processing
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_input:
                    for chunk in file.chunks():
                        temp_input.write(chunk)
                    temp_input_path = temp_input.name
                
                try:
                    # Compress
                    compressed_path = compress_video(temp_input_path)
                    
                    # Upload compressed file
                    with open(compressed_path, 'rb') as f:
                        file_id = fs.put(f, filename=file.name, content_type='video/mp4')
                    
                    # Cleanup compressed file
                    if os.path.exists(compressed_path):
                        os.remove(compressed_path)
                    print(f"DEBUG: Video compressed and uploaded successfully: {file_id}")
                except Exception as e:
                    print(f"DEBUG: Compression failed, falling back to original file: {e}")
                    # Fallback: Upload original file if compression fails
                    with open(temp_input_path, 'rb') as f:
                        file_id = fs.put(f, filename=file.name, content_type=file.content_type)
                finally:
                    # Cleanup input temp file
                    if os.path.exists(temp_input_path):
                        os.remove(temp_input_path)
            else:
                # Save image/other directly
                file_id = fs.put(file, filename=file.name, content_type=file.content_type)
            
            file_url = f"{request.scheme}://{request.get_host()}/_b_a_c_k_e_n_d/MDC_Mobile_App/file/{str(file_id)}/"
            print(f"DEBUG: File uploaded: {file_url}")
            return Response({"file_id": str(file_id), "file_url": file_url}, status=status.HTTP_201_CREATED)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.http import HttpResponse, Http404

class FileDownloadView(APIView):
    def get(self, request, file_id):
        try:
            if not ObjectId.is_valid(file_id):
                 raise Http404("Invalid file ID")
            
            grid_out = fs.get(ObjectId(file_id))
            
            response = HttpResponse(grid_out.read(), content_type=grid_out.content_type)
            response['Content-Disposition'] = f'inline; filename="{grid_out.filename}"'
            return response
        except gridfs.errors.NoFile:
            raise Http404("File not found")


class HistoryRecordingSheetView(APIView):
    """
    Fetch a History Recording Sheet by registration number.
    GET /history-sheet/?reg_no=MDC/230/2026
    """
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            collection = db['milestone_backend_historyrecordingsheet']
            record = collection.find_one({'registration_number': reg_no})
            if not record:
                return Response({"error": "History sheet not found"}, status=status.HTTP_404_NOT_FOUND)
            # Convert ObjectId to string for JSON serialization
            record['_id'] = str(record['_id'])
            
            # Clean and parse any JSON strings in the raw record
            if clean_record:
                record = clean_record(record)
            
            # Resolve creator profile from Global DB
            created_by = record.get('created_by')
            creator_profile = None
            if created_by:
                try:
                    db_global = client['Global']
                    profile_col = db_global['backend_diagnostics_profile']
                    doc = profile_col.find_one({'employeeId': str(created_by)})
                    if doc:
                        name = doc.get('employeeName', '').strip()
                        if not any(name.startswith(p) for p in ['Dr.', 'Mr.', 'Ms.', 'Mrs.']):
                            gender = doc.get('gender', '').lower()
                            prefix = 'Ms. ' if gender == 'female' else 'Mr. '
                            name = prefix + name
                        
                        quals = ', '.join([q.get('degree') for q in doc.get('qualifications', []) if q.get('degree')])
                        exp_list = doc.get('experiences', [])
                        position = exp_list[0].get('position', 'Psychologist') if exp_list else 'Psychologist'
                        
                        creator_profile = {
                            "name": name,
                            "qualifications": quals,
                            "position": position,
                            "clinic": "Milestones Developmental Center"
                        }
                except Exception:
                    pass
            record['creator_profile'] = creator_profile
            
            return Response(record)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssessmentReportView(APIView):
    """
    Fetch all Assessment Report data by registration number.
    GET /assessment-report/?reg_no=MDC/230/2026
    """
    def get(self, request):
        from datetime import datetime
        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "Registration number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Registration
            registration = db['milestone_backend_registration'].find_one({'registration_number': reg_no})
            if not registration:
                return Response({"error": "Patient registration not found"}, status=status.HTTP_404_NOT_FOUND)
            
            registration['_id'] = str(registration['_id'])
            if 'dob' in registration and registration['dob']:
                if isinstance(registration['dob'], datetime):
                    registration['dob'] = registration['dob'].isoformat()
            
            # 2. Query assessments
            physio = db['milestone_backend_physiotherapyassessment'].find_one({'registrationNumber': reg_no})
            pediatric = db['milestone_backend_pediatricassessment'].find_one({'$or': [{'registrationNumber': reg_no}, {'registration_number': reg_no}]})
            analysis = db['milestone_backend_assessmentanalysis'].find_one({'registration_number': reg_no})
            language = db['milestone_backend_childlanguageassessment'].find_one({'$or': [{'registrationNumber': reg_no}, {'registration_number': reg_no}]})
            psychology = db['milestone_backend_clinicalpsychologyassessment'].find_one({'registrationNumber': reg_no})

            if not any([physio, pediatric, analysis, language, psychology]):
                return Response({"error": "No assessments found for this patient"}, status=status.HTTP_404_NOT_FOUND)

            def serialize_doc(doc):
                if not doc:
                    return None
                doc['_id'] = str(doc['_id'])
                for date_key in ['assessment_date', 'date', 'created_date', 'lastmodified_date']:
                    if date_key in doc and isinstance(doc[date_key], datetime):
                        doc[date_key] = doc[date_key].isoformat()
                import json
                for k, v in list(doc.items()):
                    if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                        try:
                            doc[k] = json.loads(v)
                        except Exception:
                            pass
                if clean_record:
                    try:
                        doc = clean_record(doc)
                    except Exception as err:
                        print(f"Error cleaning record: {err}")
                return doc

            physio = serialize_doc(physio)
            pediatric = serialize_doc(pediatric)
            analysis = serialize_doc(analysis)
            language = serialize_doc(language)
            psychology = serialize_doc(psychology)

            # Resolve creator profile
            created_by = None
            for doc in [psychology, physio, analysis, pediatric, language]:
                if doc and doc.get('created_by'):
                    created_by = doc.get('created_by')
                    break

            creator_profile = None
            if created_by:
                try:
                    db_global = client['Global']
                    profile_col = db_global['backend_diagnostics_profile']
                    doc = profile_col.find_one({'employeeId': str(created_by)})
                    if doc:
                        name = doc.get('employeeName', '').strip()
                        if not any(name.startswith(p) for p in ['Dr.', 'Mr.', 'Ms.', 'Mrs.']):
                            gender = doc.get('gender', '').lower()
                            prefix = 'Ms. ' if gender == 'female' else 'Mr. '
                            name = prefix + name
                        
                        quals = ', '.join([q.get('degree') for q in doc.get('qualifications', []) if q.get('degree')])
                        exp_list = doc.get('experiences', [])
                        position = exp_list[0].get('position', 'Psychologist') if exp_list else 'Psychologist'
                        
                        creator_profile = {
                            "name": name,
                            "qualifications": quals,
                            "position": position,
                            "clinic": "Milestones Developmental Center"
                        }
                except Exception:
                    pass

            response_data = {
                "registration": registration,
                "physio": physio,
                "pediatric": pediatric,
                "analysis": analysis,
                "language": language,
                "psychology": psychology,
                "creator_profile": creator_profile
            }
            return Response(response_data)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientSessionAttendanceView(APIView):
    def get(self, request):
        reg_no = request.query_params.get('reg_no')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        query = {}
        if reg_no:
            query['registration_number'] = reg_no

        if year:
            try:
                yr = int(year)
                if month and month != 'All':
                    mo = int(month)
                    start_date = datetime(yr, mo, 1)
                    if mo == 12:
                        end_date = datetime(yr + 1, 1, 1)
                    else:
                        end_date = datetime(yr, mo + 1, 1)
                    query['attendance_date'] = {'$gte': start_date, '$lt': end_date}
                else:
                    start_date = datetime(yr, 1, 1)
                    end_date = datetime(yr + 1, 1, 1)
                    query['attendance_date'] = {'$gte': start_date, '$lt': end_date}
            except Exception as e:
                print(f"Error filtering dates for session attendance: {e}")

        try:
            records = list(db['milestone_backend_patientsessionattendance'].find(query).sort('attendance_date', 1))
            for r in records:
                r['_id'] = str(r['_id'])
                if 'attendance_date' in r and isinstance(r['attendance_date'], datetime):
                    r['attendance_date'] = r['attendance_date'].strftime('%Y-%m-%d')
                if 'created_date' in r and isinstance(r['created_date'], datetime):
                    r['created_date'] = r['created_date'].isoformat()
                if 'confirmed_date' in r and isinstance(r['confirmed_date'], datetime):
                    r['confirmed_date'] = r['confirmed_date'].isoformat()
            return Response(records)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        data = request.data
        try:
            res = db['milestone_backend_patientsessionattendance'].insert_one(data)
            return Response({"message": "Record created", "id": str(res.inserted_id)}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmSessionAttendanceView(APIView):
    def post(self, request, pk):
        try:
            confirmed_by = request.data.get('confirmed_by', 'Staff')
            result = db['milestone_backend_patientsessionattendance'].update_one(
                {'_id': ObjectId(pk)},
                {'$set': {
                    'is_confirmed': True,
                    'confirmed_by': confirmed_by,
                    'confirmed_date': datetime.now()
                }}
            )
            if result.matched_count == 0:
                return Response({"error": "Session record not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Session confirmed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import threading
import time

def log_notification_event(notification_id, reg_no, title, body, fcm_token, success, fcm_response, trigger_source="BACKGROUND_SCHEDULER"):
    """
    Logs every triggered push notification attempt to MongoDB collection milestone_backend_notification_logs.
    """
    try:
        log_entry = {
            "notification_id": str(notification_id or ""),
            "reg_no": str(reg_no or ""),
            "title": str(title or ""),
            "body": str(body or ""),
            "fcm_token": str(fcm_token or ""),
            "status": "SUCCESS" if success else "FAILED",
            "fcm_response": str(fcm_response or ""),
            "triggered_at": timezone.now(),
            "trigger_source": trigger_source
        }
        db['milestone_backend_notification_logs'].insert_one(log_entry)
    except Exception as e:
        print(f"Error saving notification DB log: {e}")


def process_pending_notifications(target_reg_no=None):
    """
    Scans milestone_backend_notification collection directly in MongoDB for any document 
    where members.is_send is False (created by any external admin project or system).
    Sends FCM push notification to target members and updates is_send = True & sent_datetime = NOW.
    """
    try:
        if not send_fcm_push:
            return 0

        # Bulletproof PyMongo query for documents containing unsent members (is_send is False, "false", None, or missing)
        query = {
            "$or": [
                {"members.is_send": False},
                {"members.is_send": "false"},
                {"members.is_send": "False"},
                {"members.is_send": None},
                {"members.is_send": {"$exists": False}},
                {"is_send": False}
            ]
        }
        if target_reg_no:
            clean_target = str(target_reg_no).strip()
            query["$or"].append({"members.reg_no": {"$regex": f"^{re.escape(clean_target)}$", "$options": "i"}})

        pending_docs = list(db['milestone_backend_notification'].find(query))
        now_str = timezone.now().isoformat()
        processed_count = 0


        for doc in pending_docs:
            members = doc.get('members', [])
            # Fallback if members array is empty but top-level reg_no exists
            if not members and doc.get('reg_no'):
                members = [{
                    "reg_no": doc.get('reg_no'),
                    "name": doc.get('name', ''),
                    "is_send": doc.get('is_send', False),
                    "is_read": doc.get('is_read', False)
                }]

            updated = False
            title = doc.get('title') or doc.get('heading') or doc.get('message_title') or doc.get('subject') or 'MDC Mobile'
            sub = doc.get('sub') or doc.get('body') or doc.get('message') or doc.get('description') or ''
            noti_id = str(doc.get('notification_id') or doc.get('_id') or '')

            for m in members:
                reg_no = m.get('reg_no')
                is_send = m.get('is_send', False)
                clean_reg = str(reg_no or '').strip()

                if target_reg_no and clean_reg.lower() != str(target_reg_no).strip().lower():
                    continue

                if clean_reg and is_send not in (True, "true", "True", 1):
                    # Lookup FCM token from milestone_backend_appusers with multi-fallback
                    fcm_token = None
                    user_doc = db['milestone_backend_appusers'].find_one({"reg_no": clean_reg})
                    if not user_doc or not user_doc.get('fcm_token'):
                        user_doc = db['milestone_backend_appusers'].find_one({
                            "reg_no": {"$regex": f"^{re.escape(clean_reg)}$", "$options": "i"}
                        })
                    if user_doc and user_doc.get('fcm_token'):
                        fcm_token = user_doc.get('fcm_token')
                    else:
                        try:
                            user_qs = list(appusers.objects.filter(reg_no__iexact=clean_reg))
                            if user_qs and user_qs[0].fcm_token:
                                fcm_token = user_qs[0].fcm_token
                        except Exception:
                            pass

                    if fcm_token:
                        try:
                            success, res_info = send_fcm_push(
                                fcm_token=fcm_token,
                                title=title,
                                body=sub or '',
                                data={
                                    "notification_id": noti_id,
                                    "reg_no": clean_reg,
                                    "title": title,
                                    "sub": sub or ''
                                }
                            )
                        except Exception as push_err:
                            success, res_info = False, str(push_err)

                        # Save DB Log in milestone_backend_notification_logs
                        log_notification_event(
                            notification_id=noti_id,
                            reg_no=clean_reg,
                            title=title,
                            body=sub,
                            fcm_token=fcm_token,
                            success=success,
                            fcm_response=res_info,
                            trigger_source="BACKGROUND_SCHEDULER" if not target_reg_no else "USER_POLL_FLUSH"
                        )
                        if success:
                            m['is_send'] = True
                            m['sent_datetime'] = now_str
                            updated = True
                            processed_count += 1

            if updated:
                db['milestone_backend_notification'].update_one(
                    {"_id": doc['_id']},
                    {"$set": {"members": members, "lastmodified_date": timezone.now()}}
                )

        return processed_count
    except Exception as e:
        print(f"Error in process_pending_notifications: {e}")
        return 0


_scheduler_started = False
def ensure_notification_scheduler():
    global _scheduler_started
    # In Django runserver auto-reloader, ensure thread runs in main worker process
    if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
        return

    if not _scheduler_started:
        _scheduler_started = True
        def scheduler_loop():
            print("[BACKGROUND DAEMON] Notification Loop STARTED (Polling MongoDB every 5s)")
            tick = 0
            while True:
                try:
                    tick += 1
                    count = process_pending_notifications()
                    now_time = datetime.now().strftime("%H:%M:%S")
                    if count > 0:
                        print(f"[{now_time}] [BG DAEMON TICK #{tick}] Found and pushed {count} pending notification(s)!")
                    else:
                        print(f"[{now_time}] [BG DAEMON TICK #{tick}] Polled MongoDB - No pending notifications.")
                except Exception as e:
                    print(f"Error in notification scheduler loop: {e}")
                time.sleep(5)

        t = threading.Thread(target=scheduler_loop, daemon=True)
        t.start()

ensure_notification_scheduler()








class RegisterFCMTokenView(APIView):
    """Register or update FCM Token for an app user (reg_no) and process pending unsent notifications."""
    def post(self, request):
        reg_no = request.data.get('reg_no')
        fcm_token = request.data.get('fcm_token')

        if not reg_no or not fcm_token:
            return Response({"error": "reg_no and fcm_token are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            users = list(appusers.objects.filter(reg_no=reg_no))
            if not users:
                return Response({"error": f"App user with reg_no {reg_no} not found"}, status=status.HTTP_404_NOT_FOUND)

            user = users[0]
            user.fcm_token = fcm_token
            user.lastmodified_date = timezone.now()
            user.save()

            # Automatically push any pending unsent notifications for this user now that token is registered
            pending_sent = process_pending_notifications(target_reg_no=reg_no)

            return Response({
                "message": "FCM token registered successfully",
                "reg_no": reg_no,
                "pending_notifications_sent": pending_sent
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class NotificationView(APIView):
    """
    List notifications or Create a new notification.
    On creation:
    1. Generates auto notification_id (e.g. NOTI/26/00005) if missing.
    2. Sends FCM push notification to each member in members list.
    3. Updates is_send=True and sent_datetime on successful send.
    """
    def get(self, request):
        try:
            notifications = Notification.objects.all().order_by('-created_date')
            serializer = NotificationSerializer(notifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        data = request.data.copy()
        
        # 1. Generate notification_id if missing
        if not data.get('notification_id'):
            year_str = datetime.now().strftime('%y')
            count = Notification.objects.count() + 1
            data['notification_id'] = f"NOTI/{year_str}/{count:05d}"

        title = data.get('title', '')
        sub = data.get('sub', '')
        members = data.get('members', [])

        # Process push notification for members
        now_str = datetime.now().isoformat()
        updated_members = []
        
        for member in members:
            reg_no = member.get('reg_no')
            name = member.get('name', '')
            is_send = member.get('is_send', False)
            is_read = member.get('is_read', False)
            sent_datetime = member.get('sent_datetime', None)
            read_datetime = member.get('read_datetime', None)

            # Try to send FCM push if not sent yet
            if reg_no and not is_send and send_fcm_push:
                user_qs = list(appusers.objects.filter(reg_no=reg_no))
                if user_qs and user_qs[0].fcm_token:
                    fcm_token = user_qs[0].fcm_token
                    success, res_info = send_fcm_push(
                        fcm_token=fcm_token,
                        title=title,
                        body=sub,
                        data={
                            "notification_id": data['notification_id'],
                            "reg_no": reg_no,
                            "title": title,
                            "sub": sub
                        }
                    )
                    if success:
                        is_send = True
                        sent_datetime = now_str

                    log_notification_event(
                        notification_id=data['notification_id'],
                        reg_no=reg_no,
                        title=title,
                        body=sub,
                        fcm_token=fcm_token,
                        success=success,
                        fcm_response=res_info,
                        trigger_source="POST_NOTIFICATION_API"
                    )

            updated_members.append({
                "reg_no": reg_no,
                "name": name,
                "is_send": is_send,
                "is_read": is_read,
                "sent_datetime": sent_datetime,
                "read_datetime": read_datetime
            })

        data['members'] = updated_members

        serializer = NotificationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationSendView(APIView):
    """
    Trigger manual push notification send for an existing notification document.
    """
    def post(self, request, pk):
        try:
            notification = None
            if len(pk) == 24:
                try:
                    notification = Notification.objects.get(_id=ObjectId(pk))
                except Exception:
                    pass
            if not notification:
                notification = Notification.objects.get(notification_id=pk)

            title = notification.title
            sub = notification.sub or ''
            members = notification.members or []
            now_str = datetime.now().isoformat()
            updated_any = False

            for member in members:
                reg_no = member.get('reg_no')
                if reg_no and not member.get('is_send', False) and send_fcm_push:
                    user_qs = list(appusers.objects.filter(reg_no=reg_no))
                    if user_qs and user_qs[0].fcm_token:
                        fcm_token = user_qs[0].fcm_token
                        success, res_info = send_fcm_push(
                            fcm_token=fcm_token,
                            title=title,
                            body=sub,
                            data={
                                "notification_id": notification.notification_id,
                                "reg_no": reg_no,
                                "title": title,
                                "sub": sub
                            }
                        )
                        log_notification_event(
                            notification_id=notification.notification_id,
                            reg_no=reg_no,
                            title=title,
                            body=sub,
                            fcm_token=fcm_token,
                            success=success,
                            fcm_response=res_info,
                            trigger_source="RESEND_API"
                        )
                        if success:
                            member['is_send'] = True
                            member['sent_datetime'] = now_str
                            updated_any = True

            if updated_any:
                notification.members = members
                notification.lastmodified_date = timezone.now()
                notification.save()

            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationLogsView(APIView):
    """
    Fetch push notification log history from milestone_backend_notification_logs.
    Query params: ?reg_no=MDC/155/2025
    """
    def get(self, request):
        try:
            reg_no = request.query_params.get('reg_no')
            query = {}
            if reg_no:
                query["reg_no"] = reg_no.strip()

            logs_cursor = db['milestone_backend_notification_logs'].find(query).sort("_id", -1).limit(100)
            logs_list = []
            for item in logs_cursor:
                item['id'] = str(item['_id'])
                del item['_id']
                if 'triggered_at' in item and isinstance(item['triggered_at'], datetime):
                    item['triggered_at'] = item['triggered_at'].isoformat()
                logs_list.append(item)

            return Response(logs_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class NotificationMarkReadView(APIView):
    """
    Mark a notification as read (is_read=True, read_datetime=now, read_at=now) for a specific member reg_no.
    Accepts notification_id (or _id or id) and reg_no.
    Guaranteed success with 200 OK response.
    """
    def post(self, request):
        notification_id = request.data.get('notification_id') or request.data.get('_id') or request.data.get('id')
        reg_no = (request.data.get('reg_no') or '').strip()

        if not reg_no:
            return Response({"error": "reg_no is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            now_str = timezone.now().isoformat()
            now_tz = timezone.now()

            query_list = []
            if notification_id:
                clean_id_str = str(notification_id).strip()
                query_list.append({"notification_id": clean_id_str})
                query_list.append({"_id": clean_id_str})
                if len(clean_id_str) == 24:
                    try:
                        query_list.append({"_id": ObjectId(clean_id_str)})
                    except Exception:
                        pass

            query_list.append({"members": {"$elemMatch": {"reg_no": reg_no}}})

            docs = list(db['milestone_backend_notification'].find({"$or": query_list}))

            if not docs:
                return Response({"error": "No notification documents found"}, status=status.HTTP_404_NOT_FOUND)

            updated_count = 0
            for doc in docs:
                doc_noti_id = str(doc.get('notification_id') or '')
                doc_id_str = str(doc['_id'])
                
                # If a specific notification_id was requested, filter for matching doc
                if notification_id:
                    clean_id_str = str(notification_id).strip()
                    if clean_id_str != doc_noti_id and clean_id_str != doc_id_str:
                        continue

                members = doc.get('members', [])
                member_found = False

                for member in members:
                    m_reg = (member.get('reg_no') or '').strip()
                    if m_reg == reg_no or m_reg.lower() == reg_no.lower():
                        member['is_read'] = True
                        member['read_datetime'] = now_str
                        member['read_at'] = now_str
                        member_found = True
                        break

                if not member_found:
                    members.append({
                        "reg_no": reg_no,
                        "name": "",
                        "is_send": True,
                        "is_read": True,
                        "sent_datetime": now_str,
                        "read_datetime": now_str,
                        "read_at": now_str
                    })

                db['milestone_backend_notification'].update_one(
                    {"_id": doc['_id']},
                    {"$set": {"members": members, "lastmodified_date": now_tz}}
                )
                updated_count += 1

            return Response({
                "message": "Notification marked as read successfully",
                "notification_id": str(notification_id or ''),
                "reg_no": reg_no,
                "updated_count": updated_count,
                "is_read": True,
                "read_datetime": now_str,
                "read_at": now_str
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class UserNotificationListView(APIView):
    """
    Fetch all notifications relevant for a given member reg_no.
    Returns array of notifications with member-specific is_read, is_send, sent_datetime, read_datetime, read_at status.
    Filters out notifications that have been marked as read for more than 24 hours.
    """
    def get(self, request, reg_no=None):
        if not reg_no:
            reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response({"error": "reg_no parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        reg_no = str(reg_no).rstrip('/')

        # 1. Flush & send any pending unsent notifications for this reg_no OR overall
        try:
            process_pending_notifications(target_reg_no=reg_no)
        except Exception as err:
            print(f"Error in process_pending_notifications during list fetch: {err}")


        try:
            notifications = Notification.objects.all().order_by('-created_date')
            user_notifications = []
            now = datetime.now()

            for noti in notifications:
                members = noti.members or []
                for m in members:
                    if m.get('reg_no') == reg_no:
                        is_read = m.get('is_read', False)
                        read_dt_str = m.get('read_at') or m.get('read_datetime')

                        # If notification was opened/read, check if 24 hours (86,400 seconds) have passed
                        if is_read and read_dt_str:
                            try:
                                clean_dt_str = str(read_dt_str).replace('Z', '+00:00')
                                read_dt = datetime.fromisoformat(clean_dt_str)
                                if read_dt.tzinfo is not None:
                                    read_dt = read_dt.replace(tzinfo=None)
                                elapsed_seconds = (now - read_dt).total_seconds()
                                if elapsed_seconds > 86400: # Exclude if marked as read > 24h ago
                                    continue
                            except Exception:
                                pass

                        user_notifications.append({
                            "id": str(noti._id),
                            "notification_id": noti.notification_id,
                            "title": noti.title,
                            "sub": noti.sub,
                            "created_by": noti.created_by,
                            "created_date": noti.created_date.isoformat() if noti.created_date else None,
                            "reg_no": reg_no,
                            "name": m.get('name'),
                            "is_send": m.get('is_send', False),
                            "is_read": is_read,
                            "sent_datetime": m.get('sent_datetime'),
                            "read_datetime": read_dt_str,
                            "read_at": read_dt_str
                        })
                        break

            return Response(user_notifications, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




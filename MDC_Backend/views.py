from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Registration, PatientAttendance
from .serializers import RegistrationSerializer, PatientAttendanceSerializer
import os
import traceback
from pymongo import MongoClient

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

        except Registration.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

from .models import GoalsAssessment, leaveform
from .serializers import GoalsAssessmentSerializer, LeaveFormSerializer

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

import gridfs
import certifi
from bson.objectid import ObjectId
from django.conf import settings
from dotenv import load_dotenv

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

from .utils import compress_video
import shutil
import tempfile

from rest_framework.parsers import MultiPartParser, FormParser

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

import subprocess
import os
import uuid

def compress_video(input_path):
    """
    Compresses a video file using FFmpeg.
    Returns the path to the compressed video file.
    """
    output_filename = f"{uuid.uuid4()}.mp4"
    output_path = os.path.join(os.path.dirname(input_path), output_filename)

    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "scale='min(1280,iw)':-2", # Scale to 720p if larger, maintaining aspect ratio
        "-vcodec", "libx264",
        "-crf", "28",
        "-preset", "faster", # Faster is usually lighter on memory
        "-acodec", "aac",
        "-b:a", "128k",
        "-threads", "2", # Limit threads to reduce memory footprint
        "-y", # Overwrite output file if it exists
        output_path
    ]

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error compressing video: {e}")
        if e.stderr:
            print(f"FFmpeg stderr: {e.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e

# from pathlib import Path
# from google import genai
# from google.genai import types
# from PIL import Image, ImageDraw, ImageFont
# import os
# import json
# from pydantic import BaseModel
# import cv2
# import yt_dlp
# import tempfile
# import re

# class VideoResponseFormat(BaseModel):
#     description: str
#     dark_pattern_type: str
#     confidence: int
#     bounding_box: list
#     timestamp: str

# class ImageResponseFormat(BaseModel):
#     description: str
#     dark_pattern_type: str
#     confidence: int
#     bounding_box: list

# def download_youtube_video(url, output_path=None):
#     """Download YouTube video to a temporary file."""
#     if output_path is None:
#         output_path = tempfile.mktemp(suffix='.mp4')
    
#     ydl_opts = {
#         'format': 'best[height<=720]',  # Limit to 720p for faster processing
#         'outtmpl': output_path,
#     }
    
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         ydl.download([url])
    
#     # Check if file was actually created
#     if not os.path.exists(output_path):
#         raise FileNotFoundError(f"Video download failed - file not found at {output_path}")
    
#     return output_path

# def timestamp_to_seconds(timestamp):
#     """Convert timestamp string (HH:MM:SS) to seconds."""
#     parts = timestamp.split(':')
#     if len(parts) == 3:
#         hours, minutes, seconds = map(int, parts)
#         return hours * 3600 + minutes * 60 + seconds
#     elif len(parts) == 2:
#         minutes, seconds = map(int, parts)
#         return minutes * 60 + seconds
#     else:
#         return int(parts[0])

# def extract_frame_at_timestamp(video_path, timestamp, output_path=None):
#     """Extract a frame from video at the specified timestamp."""
#     cap = cv2.VideoCapture(video_path)
    
#     if not cap.isOpened():
#         raise ValueError(f"Could not open video file: {video_path}")
    
#     # Get video properties
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
#     duration = frame_count / fps if fps > 0 else 0
    
#     # Convert timestamp to seconds
#     seconds = timestamp_to_seconds(timestamp)
    
#     # Set video position to the timestamp
#     cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    
#     # Read the frame
#     ret, frame = cap.read()
#     cap.release()
    
#     if not ret:
#         raise ValueError(f"Could not extract frame at timestamp {timestamp}")
    
#     # Convert BGR to RGB
#     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     # Convert to PIL Image
#     pil_image = Image.fromarray(frame_rgb)
    
#     # Save if output path is provided
#     if output_path:
#         pil_image.save(output_path)
    
#     return pil_image

# def analyze_youtube_video(video_url):
#     video_prompt = """
#     You are a video analysis AI. The user wants to detect and track instances of the following target object in a video:

#     Target object: Dark Patterns  
#     Types of Dark Patterns you may encounter:
#     1. Comparison Prevention
#     2. Confirmation Shaming
#     3. Disguised Ads
#     4. Fake Scarcity
#     5. Fake Social Proof
#     6. Fake Urgency
#     7. Forced Action
#     8. Hard to Cancel
#     9. Hidden Costs
#     10. Hidden Subscription
#     11. Nagging
#     12. Obstruction
#     13. Preselection
#     14. Sneaking
#     15. Trick Wording
#     16. Visual Interference

#     Your Tasks:
#     1. Detect instances of dark patterns in the video.
#     2. For each detection event, report **individually** — one event per object instance.
#     - Do not group multiple detections into one entry.
#     3. For each detection, include:
#     - Estimated timestamp (e.g., "00:00:07")
#     - The dark pattern type identified
#     - A short description of how and where it appears
#     - A bounding box in `[y_min, x_min, y_max, x_max]` format
#         - Coordinates must be **normalized to a 720p resolution** (1280x720)
#         - Origin `(0,0)` is the top-left corner of the image
#     - Confidence level (0–100 scale)

#     4. Output your results as a **JSON array**, where each element corresponds to **one detection event**, with the following fields:
#     - `"description": str`
#     - `"dark_pattern_type": str`
#     - `"confidence": int`
#     - `"bounding_box": list`
#     - `"timestamp": str`

#     Example JSON output:
#     [
#         {
#             "description": "A disguised ad appears as part of the product recommendation carousel.",
#             "dark_pattern_type": "Disguised Ads",
#             "confidence": 87,
#             "bounding_box": [0.15, 0.30, 0.25, 0.50],
#             "timestamp": "00:00:07"
#         },
#         {
#             "description": "Fake scarcity message shown below the product image.",
#             "dark_pattern_type": "Fake Scarcity",
#             "confidence": 91,
#             "bounding_box": [0.40, 0.60, 0.45, 0.75],
#             "timestamp": "00:00:12"
#         }
#     ]

#     Important:
#     - Ensure each detection is **reported separately** in the array.
#     - Follow the JSON format strictly.
#     - Keep bounding box values normalized to 720p.
#     """

#     # # Download the video
#     # print(f"Downloading video from {video_url}...")
#     # video_path = download_youtube_video(video_url)

#     client = genai.Client()
#     response = client.models.generate_content(
#         model='models/gemini-2.5-flash',
#         contents=types.Content(
#             parts=[
#                 types.Part(
#                     file_data=types.FileData(file_uri=video_url)
#                 ),
#                 types.Part(text=video_prompt)
#             ]
#         )
#     )
#     # my_dark_patterns: list[VideoResponseFormat] = response.parsed
#     print(response.text)

#     # # Extract frames and draw bounding boxes for each detected pattern
#     # for pattern in my_dark_patterns:
#     #     try:
#     #         # Extract frame at the timestamp
#     #         frame = extract_frame_at_timestamp(video_path, pattern.timestamp)
            
#     #         # Save frame to temporary file
#     #         temp_frame_path = tempfile.mktemp(suffix='.png')
#     #         frame.save(temp_frame_path)
            
#     #         # Draw bounding box on the frame
#     #         img_with_box = draw_bounding_box(
#     #             image_path=temp_frame_path,
#     #             bounding_box=pattern.bounding_box,
#     #             label=pattern.dark_pattern_type,
#     #             confidence=pattern.confidence
#     #         )
            
#     #         # Save the frame with bounding box
#     #         safe_pattern_type = ''.join(c for c in pattern.dark_pattern_type if c.isalnum() or c in '-_')
#     #         safe_timestamp = pattern.timestamp.replace(':', '-')
#     #         filename = f'video_frame_{safe_timestamp}_{safe_pattern_type}.png'
#     #         save_image_to_output(img_with_box, filename)
#     #         print(f'Saved frame with bounding box: {filename}')
            
#     #         # Clean up temporary frame file
#     #         try:
#     #             os.remove(temp_frame_path)
#     #         except:
#     #             pass
                
#     #     except Exception as e:
#     #         print(f"Failed to process frame at {pattern.timestamp}: {str(e)}")

#     # # Clean up the downloaded video
#     # try:
#     #     os.remove(video_path)
#     # except:
#     #     pass

# # def analyze_video(object_description, video_path):
# #     video_prompt = """
# #     You are a video analysis AI. The user wants to locate and track the object described below:

# #     Target object: "{object_description}"

# #     Tasks:
# #     1. Find the object in the video and summarize where and how it appears.
# #     2. Track the object through time and identify 3–7 key events. For each event:
# #         - Provide an estimated timestamp (e.g., "00:00:07")
# #         - Describe what the object is doing
# #         - Include a bounding box in y_min, x_min, y_max, x_max format with a label and confidence level
# #         - Coordinates must be normalized to a 0–1000 scale
# #         - Origin is the top-left of the image
# #     """

# #     client = genai.Client()
# #     response = client.models.generate_content(
# #         model='models/gemini-2.5-flash',
# #         contents=types.Content(
# #             parts=[
# #                 types.Part(
# #                     file_data=types.FileData(file_uri='https://www.youtube.com/watch?v=T3qH-uY3t-Y&ab_channel=monday.com')
# #                 ),
# #                 types.Part(text=video_prompt.format(object_description=object_description))
# #             ]
# #         )
# #     )
# #     print(response.text)


# def analyze_image(image_path):
#     text_prompt = """
#     You are an image analysis AI. The user wants to analyze the following:

#     Target object: Dark Patterns
#     Type of Dark Patterns:
#     1. Comparison Prevention
#     2. Confirmation Shaming
#     3. Disguised Ads
#     4. Fake scarcity
#     5. Fake social proof
#     6. Fake urgency
#     7. Forced action
#     8. Hard to cancel
#     9. Hidden costs
#     10. Hidden subscription
#     11. Nagging
#     12. Obstruction
#     13. Preselection
#     14. Sneaking
#     15. Trick Wording
#     16. Visual interference

#     Tasks:
#     1. Find the object in the image and summarize where and how it appears.
#     2. Describe what the object is doing in detail.
#     3. Return your answer as a JSON object with the following fields:
#         description: str
#         dark_pattern_type: str
#         confidence: int
#         bounding_box: list
#     Notes:
#     - The bounding box must be in y_min, x_min, y_max, x_max format, normalized to a 0–1000 scale.
#     - The origin is the top-left of the image.
#     """

#     client = genai.Client()
#     with open(image_path, 'rb') as f:
#         image_bytes = f.read()

#     response = client.models.generate_content(
#         model='gemini-2.5-flash',
#         contents=[
#             types.Part.from_bytes(
#                 data=image_bytes,
#                 mime_type='image/png'
#             ),
#             types.Part(text=text_prompt)
#         ],
#         config={
#             "response_mime_type": "application/json",
#             "response_schema": list[ImageResponseFormat]
#         }
#     )

#     # Try to parse the JSON from the response
#     try:
#         my_dark_patterns: list[ImageResponseFormat] = response.parsed
#         for tmp_result in my_dark_patterns:
#             img = draw_bounding_box(
#                 image_path=image_path,
#                 bounding_box=tmp_result.bounding_box,
#                 label=tmp_result.dark_pattern_type,
#                 confidence=tmp_result.confidence
#             )
#             # Remove special characters from dark_pattern_type to ensure valid filename
#             safe_pattern_type = ''.join(c for c in tmp_result.dark_pattern_type if c.isalnum() or c in '-_')
#             filename = f'{Path(image_path).stem}_{safe_pattern_type}.png'
#             save_image_to_output(img, filename)
#             print(f'Saved image to {filename}')
#     except Exception as e:
#         print("Failed to parse JSON or draw bounding box:", e)

# def draw_bounding_box(image_path, bounding_box, label, confidence):
#     """
#     Draws a bounding box with label and confidence on the image.
#     Args:
#         image_path (str): Path to the input image.
#         bounding_box (list): [y_min, x_min, y_max, x_max] in 0-1000 scale.
#         label (str): Label for the bounding box.
#         confidence (float): Confidence value (0-100).
#     Returns:
#         Image object with bounding box drawn.
#     """
#     image = Image.open(image_path).convert('RGB')
#     draw = ImageDraw.Draw(image)
#     width, height = image.size

#     # Convert normalized coordinates to pixel values
#     y_min, x_min, y_max, x_max = bounding_box
    
#     y_min = int(y_min / 1000 * height)
#     y_max = int(y_max / 1000 * height)
#     x_min = int(x_min / 1000 * width)
#     x_max = int(x_max / 1000 * width)

#     # Draw rectangle
#     draw.rectangle((x_min, y_min, x_max, y_max), outline='red', width=3)

#     # Prepare label text
#     text = f"{label} ({confidence}%)"
#     try:
#         font = ImageFont.truetype("arial.ttf", 20)
#     except:
#         font = ImageFont.load_default()
#     # Calculate text size using textbbox for compatibility
#     text_bbox = draw.textbbox((x_min, y_min), text, font=font)
#     text_width = text_bbox[2] - text_bbox[0]
#     text_height = text_bbox[3] - text_bbox[1]
#     text_bg = (x_min, y_min - text_height, x_min + text_width, y_min)
#     draw.rectangle(text_bg, fill='red')
#     draw.text((x_min, y_min - text_height), text, fill='white', font=font)

#     return image

# def save_image_to_output(image, filename):
#     """
#     Saves the image to the output folder, creating it if necessary.
#     Args:
#         image (PIL.Image): Image object to save.
#         filename (str): Name of the file to save as.
#     """
#     output_dir = 'output'
#     os.makedirs(output_dir, exist_ok=True)
#     output_path = os.path.join(output_dir, filename)
#     image.save(output_path)


# if __name__ == '__main__':
#     analyze_youtube_video('https://www.youtube.com/watch?v=K-j7Ty2rHBc&ab_channel=KevinStratvert')
#     # analyze_image('reference/comparison-prevention.png')

#     # Process all deceptive_design files in reference directory
#     # reference_dir = 'reference'
#     # if os.path.exists(reference_dir):
#     #     for filename in os.listdir(reference_dir):
#     #         if filename.startswith('deceptive_design') and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
#     #             file_path = os.path.join(reference_dir, filename)
#     #             print(f"Processing {filename}...")
#     #             analyze_image(file_path)
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
import json
import os
import cv2
import yt_dlp
import tempfile

client = genai.Client()

def parse_json(json_output: str):
    """Parse JSON output by removing markdown fencing."""
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line == "```json":
            json_output = "\n".join(lines[i+1:])  # Remove everything before "```json"
            json_output = json_output.split("```")[0]  # Remove everything after the closing "```"
            break  # Exit the loop once "```json" is found
    return json_output

def timestamp_to_seconds(timestamp):
    """Convert timestamp string (HH:MM:SS) to seconds."""
    parts = timestamp.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        return int(parts[0])

def extract_frame_at_timestamp(video_path, timestamp, output_path=None):
    """Extract a frame from video at the specified timestamp."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    # Convert timestamp to seconds
    seconds = timestamp_to_seconds(timestamp)
    print(f"Extracting frame at timestamp: {timestamp} (seconds: {seconds})")
    
    # Set video position to the timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    
    # Read the frame
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError(f"Could not extract frame at timestamp {timestamp}")
    
    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_image = Image.fromarray(frame_rgb)
    
    # Save if output path is provided
    if output_path:
        pil_image.save(output_path)
    
    return pil_image

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

def draw_bounding_box(image_path, bounding_box, label):
    """
    Draws a bounding box with label on the image.
    Args:
        image_path (str): Path to the input image.
        bounding_box (list): [y_min, x_min, y_max, x_max] in 0-1000 scale.
        label (str): Label for the bounding box.
    Returns:
        Image object with bounding box drawn.
    """
    image = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Convert normalized coordinates to pixel values
    y_min, x_min, y_max, x_max = bounding_box
    
    y_min = int(y_min / 1000 * height)
    y_max = int(y_max / 1000 * height)
    x_min = int(x_min / 1000 * width)
    x_max = int(x_max / 1000 * width)

    # Draw rectangle
    draw.rectangle((x_min, y_min, x_max, y_max), outline='red', width=3)

    # Prepare label text
    text = f"{label}"
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Calculate text size using textbbox for compatibility
    text_bbox = draw.textbbox((x_min, y_min), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_bg = (x_min, y_min - text_height, x_min + text_width, y_min)
    draw.rectangle(text_bg, fill='red')
    draw.text((x_min, y_min - text_height), text, fill='white', font=font)

    return image

def save_image_to_output(image, filename):
    """
    Saves the image to the output folder, creating it if necessary.
    Args:
        image (PIL.Image): Image object to save.
        filename (str): Name of the file to save as.
    """
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    image.save(output_path)

def analyze_video(video_path: str, start_offset: str, end_offset: str):
    """Analyze YouTube video for dark patterns."""
    prompt = """
    Give the detections for dark patterns.
    Type of Dark Patterns:
    1. Comparison Prevention
    2. Confirmation Shaming
    3. Disguised Ads
    4. Fake scarcity
    5. Fake social proof
    6. Fake urgency
    7. Forced action
    8. Hard to cancel
    9. Hidden costs
    10. Hidden subscription
    11. Nagging
    12. Obstruction
    13. Preselection
    14. Sneaking
    15. Trick Wording
    16. Visual interference
    
    Tasks:
    1. Find the dark pattern in the video.
    2. Track the dark pattern through time and identify 3–20 key events.
    3. Reply in JSON format. 
        For each event, provide a json output with the following fields:
            - timestamp: Provide an estimated timestamp in seconds (e.g., "00:00:07")
            - type: The type of dark pattern
            - description: Describe what the dark pattern is doing at that timestamp
            - bounding_box: Include a bounding box in y_min, x_min, y_max, x_max format
    4. The origin is the top-left of the image.
    5. The video resolution is 640 x 360.
    """

    # Only for videos of size <20Mb
    video_bytes = open(video_path, 'rb').read()
    response = client.models.generate_content(
        model='models/gemini-2.5-flash',
        contents=types.Content(
            parts=[
                types.Part(
                    inline_data=types.Blob(data=video_bytes, mime_type='video/mov'),
                    video_metadata=types.VideoMetadata(
                        start_offset=start_offset,
                        end_offset=end_offset
                    )
                ),
                types.Part(text=prompt)
            ]
        )
    )
    print(response.text)
    items = json.loads(parse_json(response.text))
    
    # # Download the video
    # print(f"Downloading video from {video_url}...")
    # video_path = download_youtube_video(video_url)

    # Extract frames and draw bounding boxes for each detected pattern
    for item in items:
        try:
            # Extract frame at the timestamp
            frame = extract_frame_at_timestamp(video_path, item["timestamp"])
            
            # Save frame to temporary file
            temp_frame_path = tempfile.mktemp(suffix='.png')
            frame.save(temp_frame_path)
            
            # Draw bounding box on the frame
            img_with_box = draw_bounding_box(
                image_path=temp_frame_path,
                bounding_box=item["bounding_box"],
                label=item["type"],
            )
            
            # Save the frame with bounding box
            safe_pattern_type = ''.join(c for c in item["type"] if c.isalnum() or c in '-_')
            safe_timestamp = item["timestamp"].replace(':', '-')
            filename = f'file_video_frame_{safe_timestamp}_{safe_pattern_type}.png'
            save_image_to_output(img_with_box, filename)
            print(f'Saved frame with bounding box: {filename}')
            
            # Clean up temporary frame file
            # try:
            #     os.remove(temp_frame_path)
            # except:
            #     pass
                
        except Exception as e:
            print(f"Failed to process frame at {item['timestamp']}: {str(e)}")

    # # Clean up the downloaded video
    # try:
    #     os.remove(video_path)
    # except:
    #     pass

if __name__ == "__main__":
    analyze_video('reference/videos/random_sgcarmart-2.mov', '0s', '63s')
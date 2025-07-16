import dataclasses
from typing import Tuple
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageColor
import io
import base64
import json
import numpy as np
import os

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

@dataclasses.dataclass(frozen=True)
class SegmentationMask:
    # bounding box pixel coordinates (not normalized)
    y0: int  # in [0..height - 1]
    x0: int  # in [0..width - 1]
    y1: int  # in [0..height - 1]
    x1: int  # in [0..width - 1]
    mask: np.ndarray  # [img_height, img_width] with values 0..255
    label: str

def extract_segmentation_masks(im: Image.Image, output_dir: str = "segmentation_outputs"):
    """Extract segmentation masks for dark patterns from an image."""
    im.thumbnail([1024, 1024], Image.Resampling.LANCZOS)

    prompt = """
    Give the segmentation masks for dark patterns.
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
    Output a JSON list of segmentation masks where each entry contains the 2D
    bounding box in the key "box_2d", the segmentation mask in key "mask", and
    the text label in the key "label". Use descriptive labels.
    """

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),  # set thinking_budget to 0 for better results in object detection
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, im],  # Pillow images can be directly passed as inputs (which will be converted by the SDK)
        config=config
    )

    # Parse JSON response
    items = json.loads(parse_json(response.text))

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Process each mask
    masks = []
    for i, item in enumerate(items):
        # Get bounding box coordinates
        box = item["box_2d"]
        y0 = int(box[0] / 1000 * im.size[1])
        x0 = int(box[1] / 1000 * im.size[0])
        y1 = int(box[2] / 1000 * im.size[1])
        x1 = int(box[3] / 1000 * im.size[0])

        # Skip invalid boxes
        if y0 >= y1 or x0 >= x1:
            continue

        # Process mask
        png_str = item["mask"]
        if not png_str.startswith("data:image/png;base64,"):
            continue

        # Remove prefix
        png_str = png_str.removeprefix("data:image/png;base64,")
        mask_data = base64.b64decode(png_str)
        mask = Image.open(io.BytesIO(mask_data))

        # Resize mask to match bounding box
        mask = mask.resize((x1 - x0, y1 - y0), Image.Resampling.BILINEAR)
        np_mask = np.zeros((im.size[1], im.size[0]), dtype=np.uint8)
        np_mask[y0:y1, x0:x1] = mask
        masks.append(SegmentationMask(y0, x0, y1, x1, np_mask, item["label"]))

    return masks

def overlay_mask_on_img(
    img: Image.Image,
    mask: np.ndarray,
    color: str,
    alpha: float = 0.7
) -> Image.Image:
    """
    Overlays a single mask onto a PIL Image using a named color.

    The mask image defines the area to be colored. Non-zero pixels in the
    mask image are considered part of the area to overlay.

    Args:
        img: The base PIL Image object.
        mask: A numpy array representing the mask.
                Should have the same height and width as the img.
                Values 0-255 where non-zero pixels indicate the masked area.
        color: A standard color name string (e.g., 'red', 'blue', 'yellow').
        alpha: The alpha transparency level for the overlay (0.0 fully
                transparent, 1.0 fully opaque). Default is 0.7 (70%).

    Returns:
        A new PIL Image object (in RGBA mode) with the mask overlaid.

    Raises:
        ValueError: If color name is invalid, mask dimensions mismatch img
                    dimensions, or alpha is outside the 0.0-1.0 range.
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("Alpha must be between 0.0 and 1.0")

    # Convert the color name string to an RGB tuple
    try:
        color_rgb: Tuple[int, int, int] = ImageColor.getrgb(color)
    except ValueError as e:
        # Re-raise with a more informative message if color name is invalid
        raise ValueError(f"Invalid color name '{color}'. Supported names are typically HTML/CSS color names. Error: {e}")

    # Prepare the base image for alpha compositing
    img_rgba = img.convert("RGBA")
    width, height = img_rgba.size

    # Create the colored overlay layer
    # Calculate the RGBA tuple for the overlay color
    alpha_int = int(alpha * 255)
    overlay_color_rgba = color_rgb + (alpha_int,)

    # Create an RGBA layer (all zeros = transparent black)
    colored_mask_layer_np = np.zeros((height, width, 4), dtype=np.uint8)

    # Mask has values between 0 and 255, threshold at 127 to get binary mask.
    mask_np_logical = mask > 127

    # Apply the overlay color RGBA tuple where the mask is True
    colored_mask_layer_np[mask_np_logical] = overlay_color_rgba

    # Convert the NumPy layer back to a PIL Image
    colored_mask_layer_pil = Image.fromarray(colored_mask_layer_np, 'RGBA')

    # Composite the colored mask layer onto the base image
    result_img = Image.alpha_composite(img_rgba, colored_mask_layer_pil)

    return result_img

def plot_segmentation_masks(img: Image.Image, segmentation_masks: list[SegmentationMask]):
    """
    Plots bounding boxes on an image with markers for each a name, using PIL, normalized coordinates, and different colors.

    Args:
        img: The PIL Image.
        segmentation_masks: A list of SegmentationMask objects containing the name of the object,
            their positions, and the segmentation mask.
    """
    # Define a list of colors
    colors = [
        'red', 'green', 'blue', 'yellow', 'orange', 'pink', 'purple', 'brown',
        'gray', 'beige', 'turquoise', 'cyan', 'magenta', 'lime', 'navy', 'maroon',
        'teal', 'olive', 'coral', 'lavender', 'violet', 'gold', 'silver',
    ]
    font = ImageFont.truetype("Arial Bold.ttf", size=14)

    # Do this in 3 passes to make sure the boxes and text are always visible.

    # Overlay the mask
    for i, mask in enumerate(segmentation_masks):
        color = colors[i % len(colors)]
        img = overlay_mask_on_img(img, mask.mask, color)

    # Create a drawing object
    draw = ImageDraw.Draw(img)

    # Draw the bounding boxes
    for i, mask in enumerate(segmentation_masks):
        color = colors[i % len(colors)]
        draw.rectangle(
            ((mask.x0, mask.y0), (mask.x1, mask.y1)), outline=color, width=4
        )

    # Draw the text labels
    for i, mask in enumerate(segmentation_masks):
        color = colors[i % len(colors)]
        if mask.label != "":
            draw.text((mask.x0 + 8, mask.y0 - 20), mask.label, fill=color, font=font)
    return img

# Example usage
if __name__ == "__main__":
    import os
    from pathlib import Path
    
    # Create output directory if it doesn't exist
    output_dir = Path("output/images_mask")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all files in reference folder
    reference_dir = Path("reference/images")
    for file_path in reference_dir.iterdir():
        if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            im = Image.open(file_path)
            segmentation_masks = extract_segmentation_masks(im)
            new_image = plot_segmentation_masks(im, segmentation_masks)
            
            # Save with masks_ prefix
            output_filename = f"masks_{file_path.name}"
            new_image.save(output_dir / output_filename)

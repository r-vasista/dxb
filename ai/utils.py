from PIL import Image
import base64
from io import BytesIO
from openai import OpenAI
from django.conf import settings
import json

OPEN_AI_KEY = settings.OPEN_AI_KEY

client = OpenAI(api_key=OPEN_AI_KEY)

def compress_and_encode_image(file_obj, max_size=(1000, 1000), quality=85):
    """
    Accepts a Django InMemoryUploadedFile, compresses, resizes,
    and returns a base64-encoded JPEG data URI.
    """
    # Open the image
    img = Image.open(file_obj)
    
    # Convert to RGB (JPEG doesn't support transparency)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize the image while preserving aspect ratio
    img.thumbnail(max_size, Image.LANCZOS)

    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    # Encode to base64
    encoded_string = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"


def parse_gpt_response(text):
    """
    Handles GPT output in two formats:
      1. JSON-like string: {"caption": "...", "hash_tags": "...", "art_style": "..."}
      2. Old plain text format with hashtags and art_style lines.

    Returns a dictionary with:
      - description (string)
      - hashtags (list of tags without "#")
      - art_style (list of styles)
    """
    # --- Case 1: JSON-like string ---
    try:
        parsed = json.loads(text)
        description = parsed.get("description", "").strip()
        # Split hashtags string into a list, strip "#" and spaces
        hashtags = [tag.lstrip("#").strip() for tag in parsed.get("hash_tags", "").split() if tag.strip()]
        # Split art_style into a list
        art_style = [style.strip() for style in parsed.get("art_style", "").split(",") if style.strip()]
        return {
            "description": description,
            "hashtags": hashtags,
            "art_types": art_style
        }
    except json.JSONDecodeError:
        # --- Case 2: Old plain text parsing ---
        lines = text.strip().splitlines()
        description_lines = []
        hashtags = []
        art_style = []

        for line in lines:
            line = line.strip()

            if line.startswith("#"):
                hashtags += [tag.lstrip("#") for tag in line.split() if tag.strip()]
                continue

            if line.lower().startswith("**art style:**") or line.lower().startswith("art_style:"):
                raw_style = line.split(":", 1)[-1].strip()
                art_style = [s.strip() for s in raw_style.split(",") if s.strip()]
                continue

            if line:
                description_lines.append(line)

        return {
            "description": " ".join(description_lines),
            "hashtags": hashtags,
            "art_style": art_style
        }
    
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

    
def get_ai_response(gpt_model, prompt_instruction, user_content):
    response = client.responses.create(
        model=gpt_model,
        input=[
            {
                "role": "developer",
                "content": prompt_instruction
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    return response
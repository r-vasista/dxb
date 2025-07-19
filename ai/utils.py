from PIL import Image
import base64
from io import BytesIO
from openai import OpenAI
from django.conf import settings

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
    Splits a GPT response into description and list of hashtags.
    Assumes hashtags start with a line beginning with "#"
    """
    lines = text.strip().splitlines()
    description_lines = []
    hashtags = []

    for line in lines:
        if line.strip().startswith("#"):
            hashtags += line.strip().split()
        else:
            description_lines.append(line.strip())

    return {
        "description": " ".join(description_lines),
        "hashtags": hashtags
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
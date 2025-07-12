from PIL import Image
import base64
from io import BytesIO

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

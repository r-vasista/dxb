# views.py
import base64
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI

from ai.models import ArtImagePrompt
from ai.utils import compress_and_encode_image
from core.services import get_user_profile, success_response, error_response
from django.conf import settings

OPEN_AI_KEY = settings.OPEN_AI_KEY

client = OpenAI(api_key=OPEN_AI_KEY)

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

class ArtImageDescribeAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        image = request.FILES.get('image')

        if not image:
            return Response({"error": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            base64_image = compress_and_encode_image(image)
            gpt_model="gpt-4.1"
            
            prompt_instruction = (
                "You are an expert art critic and creative writer for a digital art platform. "
                "When shown an image, describe it vividly and artistically as if you're introducing the work in a gallery. "
                "Keep it short less than 2 lines, elegant, and evocative. After the description, suggest 5 relevant social media hashtags for discovery. "
                "Do not ask questions or wait for input. Respond in one go."
            )
            
            response = client.responses.create(
                model=gpt_model,
                input=[
                    {
                        "role": "developer",
                        "content": prompt_instruction
                    },
                    {
                        "role": "user",
                        "content": [
                                {
                                    "type": "input_image",
                                    "image_url": base64_image
                                }
                            ]
                    }
                ]
            )
            result_text = response.output_text
            
            # Save record
            art_prompt = ArtImagePrompt.objects.create(
                profile= get_user_profile(request.user) if request.user.is_authenticated else None,
                image=image,
                prompt=prompt_instruction,
                response=response,
                response_text=result_text,
                gpt_model = gpt_model,
                input_tokens = response.usage.input_tokens,
                output_tokens = response.usage.output_tokens,
                total_tokens = response.usage.total_tokens,

            )
            
            return Response(success_response(result_text))
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Rest framework importsrt base64
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from openai import OpenAI
import json

# Local imports
from ai.models import ArtImagePrompt, BaseAIConfig, EventTagPrompt, EventDescriptionPrompt
from ai.choices import AiUseTypes
from ai.utils import compress_and_encode_image, parse_gpt_response, get_ai_response, encode_image
from core.services import get_user_profile, success_response, error_response


class ArtImageDescribeAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        image = request.FILES.get('image')

        if not image:
            return Response({"error": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ai_config = BaseAIConfig.objects.get(use_type=AiUseTypes.IMAGE_DESCRIPTION, is_active=True)
            base64_image = compress_and_encode_image(image)
            gpt_model= ai_config.gpt_model
            
            prompt_instruction = ai_config.prompt
            user_content= [
                                {
                                    "type": "input_image",
                                    "image_url": base64_image
                                }
                            ]
            response = get_ai_response(gpt_model=gpt_model, prompt_instruction=prompt_instruction, user_content=user_content)
            
            result_text = parse_gpt_response(response.output_text)
            
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


class EventTagAIAPIView(APIView):
    """
    This API returns hash tags based on the event title and description
    """
    
    def post(self, request):
        try:
            data = request.data
            title = data.get('title', '')
            description = data.get('description', '')
            ai_config = BaseAIConfig.objects.get(use_type=AiUseTypes.EVENT_TAG)
            gpt_model = ai_config.gpt_model
            prompt_instruction = ai_config.prompt
            user_content = f"title: {title}, description: {description}"
            
            response = get_ai_response(gpt_model=gpt_model, prompt_instruction=prompt_instruction, user_content=user_content)
            result_text = parse_gpt_response(response.output_text)
            
            EventTagPrompt.objects.create(
                profile= get_user_profile(request.user) if request.user.is_authenticated else None,
                use_type = AiUseTypes.EVENT_TAG,
                description=ai_config.description,
                prompt=prompt_instruction,
                response=response,
                response_text=result_text,
                gpt_model = gpt_model,
                input_tokens = response.usage.input_tokens,
                output_tokens = response.usage.output_tokens,
                total_tokens = response.usage.total_tokens,
                event_name = title,
                event_description = description
            )
            return Response(success_response(result_text))
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventDescriptionAIAPIView(APIView):
    """
    This API returns hash tags based on the event title and description
    """
    
    def post(self, request):
        try:
            data = request.data
            event_data = data.get('event_data', '')
            ai_config = BaseAIConfig.objects.get(use_type=AiUseTypes.EVENT_DESCRIPTION)
            gpt_model = ai_config.gpt_model
            prompt_instruction = ai_config.prompt
            content = json.dumps(event_data, indent=2)
            
            response = get_ai_response(gpt_model=gpt_model, prompt_instruction=prompt_instruction, user_content=content)
            result_text = parse_gpt_response(response.output_text)
            
            EventDescriptionPrompt.objects.create(
                profile= get_user_profile(request.user) if request.user.is_authenticated else None,
                use_type = AiUseTypes.EVENT_DESCRIPTION,
                description=ai_config.description,
                prompt=prompt_instruction,
                response=response,
                response_text=result_text,
                gpt_model = gpt_model,
                input_tokens = response.usage.input_tokens,
                output_tokens = response.usage.output_tokens,
                total_tokens = response.usage.total_tokens,
                event_data=content
            )
           
            return Response(success_response(result_text))
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
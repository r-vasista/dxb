import json
import os
import io
from PIL import Image
from moviepy.editor import VideoFileClip
from django.core.files.uploadedfile import InMemoryUploadedFile
from tempfile import NamedTemporaryFile
from django.utils import timezone
from core.models import Country, State, City, WeeklyChallenge

def normalize_name(name):
    return name.strip().lower()

def import_location_data(json_path):
    """
    Imports countries, states, and cities from a nested JSON file.
    """
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    for country_data in data:
        country, _ = Country.objects.get_or_create(
            name=country_data['name'].strip(),
            code=country_data['iso3'].strip()
        )

        state_names_seen = set()

        for state_data in country_data.get('states', []):
            state_name = normalize_name(state_data['name'])

            if (state_name, country.id) in state_names_seen:
                print(f"⚠️ Duplicate state skipped: {state_data['name']} in {country.name}")
                continue

            state_names_seen.add((state_name, country.id))

            state, _ = State.objects.get_or_create(
                name=state_data['name'].strip(),
                code=(state_data.get('state_code') or '').strip(),
                country=country
            )

            city_names_seen = set()

            for city_data in state_data.get('cities', []):
                city_name = normalize_name(city_data['name'])

                if (city_name, state.id, country.id) in city_names_seen:
                    print(f"⚠️ Duplicate city skipped: {city_data['name']} in {state.name}, {country.name}")
                    continue

                city_names_seen.add((city_name, state.id, country.id))

                City.objects.get_or_create(
                    name=city_data['name'].strip(),
                    state=state,
                    country=country,
                    latitude=city_data.get('latitude') or None,
                    longitude=city_data.get('longitude') or None
                )

    print("✅ Data import completed.")

def get_user(profile):
    if profile.user:
        user=profile.user
    else:
        user=profile.organization.user
    return user

def update_last_active(profile):
    profile.last_active_at = timezone.now()
    profile.save(update_fields=["last_active_at"])

def get_inactivity_email_context(profile):
    
    # To avoid circular import error
    from post.models import Post
    
    user_name = profile.username or "Artist"
    challenge = WeeklyChallenge.objects.filter(is_active=True).first()
    challenge_hashtag = challenge.hashtag if challenge else "weeklychallenge"

    top_posts = Post.objects.filter(status='published').order_by('-reaction_count')[:3]
    top_titles = [p.title or p.caption[:40] for p in top_posts]

    return {
        "user_name": user_name,
        "challenge_hashtag": challenge_hashtag,
        "top_posts": top_titles,
    }


# Helper: get file extension
def get_extension(file):
    return os.path.splitext(file.name)[1].lower()


def is_image(file):
    return get_extension(file) in ['.jpg', '.jpeg', '.png', '.webp']


def is_video(file):
    return get_extension(file) in ['.mp4', '.mov', '.avi', '.mkv', '.webm']


def is_audio(file):
    return get_extension(file) in ['.mp3', '.wav']


def is_document(file):
    return get_extension(file) in [
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt'
    ]

# Resize image only to reduce file size (not dimensions)
def resize_image(image_file, max_mb=10):
    size_in_mb = image_file.size / (1024 * 1024)
    if size_in_mb <= max_mb:
        return image_file

    try:
        img = Image.open(image_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)  # Keep original size, reduce quality
        buffer.seek(0)

        return InMemoryUploadedFile(
            buffer,
            field_name=None,  # <- Fix this line
            name=image_file.name,
            content_type='image/jpeg',
            size=buffer.tell(),
            charset=None
        )

    except Exception as e:
        print(f"[Image Resize Error] {e}")
        return image_file

# Compress video with same dimensions, reduce bitrate only
def compress_video(video_file, max_mb=20):
    size_in_mb = video_file.size / (1024 * 1024)
    if size_in_mb <= max_mb:
        return video_file

    try:
        temp_input = NamedTemporaryFile(delete=False, suffix=get_extension(video_file))
        for chunk in video_file.chunks():
            temp_input.write(chunk)
        temp_input.close()

        clip = VideoFileClip(temp_input.name)

        temp_output = NamedTemporaryFile(delete=False, suffix=".mp4")
        clip.write_videofile(
            temp_output.name,
            codec="libx264",
            audio_codec="aac",
            bitrate="500k",  # Compress video using bitrate
            verbose=False,
            logger=None
        )

        temp_output.seek(0)
        return InMemoryUploadedFile(
            file=open(temp_output.name, 'rb'),
            field_name=None,  # <- Fix this line
            name=video_file.name,
            content_type='video/mp4',
            size=os.path.getsize(temp_output.name),
            charset=None
        )


    except Exception as e:
        print(f"[Video Compression Error] {e}")
        return video_file

# ✅ Unified Function
def process_media_file(media_file):
    if is_image(media_file):
        return resize_image(media_file), 'image'      
    elif is_video(media_file):
        return compress_video(media_file), 'video'     
    elif is_audio(media_file):
        return media_file, 'audio' 
    elif is_document(media_file):
        return media_file, 'document'
    else:
        return media_file, 'unknown'                   

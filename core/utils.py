import json
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
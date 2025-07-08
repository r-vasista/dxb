import json
from core.models import Country, State, City  # Replace 'core' with your app name

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

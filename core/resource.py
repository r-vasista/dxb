from import_export import resources
from .models import WeeklyChallenge

class WeeklyChallengeResource(resources.ModelResource):
    class Meta:
        model = WeeklyChallenge
        import_id_fields = ['hashtag']
        fields = ('title', 'description', 'hashtag', 'start_date', 'end_date', 'is_active')

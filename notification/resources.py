from import_export import resources
from .models import DailyQuote

class DailyQuoteResource(resources.ModelResource):
    def get_instance(self, instance_loader, row):
        """
        Skip import if quote with same 'text' already exists.
        """
        text = row.get('text')
        if text:
            try:
                return DailyQuote.objects.get(text=text)
            except DailyQuote.DoesNotExist:
                return None
        return None

    class Meta:
        model = DailyQuote
        import_id_fields = ['text']
        fields = ['text', 'author']
        skip_unchanged = True
        report_skipped = True

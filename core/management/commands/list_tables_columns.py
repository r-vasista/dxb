from  django.core.management.base import BaseCommand
from django.db import models
from django.apps import apps

class Command(BaseCommand):
    help = 'List all tables and their columns in the database'

    def handle(self, *args, **kwargs):

        for app_config in apps.get_app_configs():
            app_label= app_config.label
            self.stdout.write(f"App: {app_label}")

            for model in app_config.get_models():
                model_name =model._meta.model_name
                table_name=model._meta.db_table
                self.stdout.write(f"\tModel: {model_name} (Table: {table_name})")

                for field in model._meta.fields:
                    field_name = field.name
                    field_type = field.get_internal_type()
                    self.stdout.write(f"\t\tColumn: {field_name} (Type: {field_type})")
        self.stdout.write("\n")













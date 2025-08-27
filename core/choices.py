from django.db import models


class ReportReason(models.TextChoices):
    SPAM = "SPAM", "Spam / misleading"
    ABUSE = "ABUSE", "Abusive / harassing"
    HATE = "HATE", "Hate / violent speech"
    SEXUAL = "SEXUAL", "Sexual / explicit"
    ILLEGAL = "ILLEGAL", "Illegal activity"
    FRAUD = "FRAUD", "Fraud / scam"
    OTHER = "OTHER", "Other"
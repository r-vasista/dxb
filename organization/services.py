from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_email(subject, text_content, template_address, context, to_email_list):
    from_email = settings.EMAIL_HOST_USER
    html_content = render_to_string(template_address, context)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
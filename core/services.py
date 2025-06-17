from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.conf import settings

def success_response(data):
    return {"status": True, "data":data}

def error_response(message):
    return {"status": False, "message":message}

def send_custom_email(subject, text_content, template_address, context, recipient_list):
    try:
        # HTML version (Load from template or write inline)
        html_content = render_to_string(template_address, context)

        from_email = settings.EMAIL_HOST_USER

        # Create email object
        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")  # Attach HTML version

        # Send email
        email.send()
        return True, 'success'
    except TemplateDoesNotExist:
        return False, "Error: Template does not exist."
    except TemplateSyntaxError:
        return False, "Error: Template Syntax error"
    except Exception as e:
        return False, str(e)

def get_user_profile(user):
    # Fetch profile (either directly or via organization)
    profile = getattr(user, "profile", None)

    if not profile and hasattr(user, "organization"):
        profile = getattr(user.organization, "profile", None)
    
    return profile
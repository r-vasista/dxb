from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.template import Template, Context

from core.models import EmailTemplate, EmailConfiguration
from post.models import Hashtag, ArtType


import re

def success_response(data, message = None):
    return {"status": True, "data":data, "message":message}

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


def send_dynamic_email_using_template(template_name, recipient_list, context={}):
    """
    Example usage:
    send_dynamic_email_using_template(
        template_name="register-otp",
        recipient_list=["vasista.rachaputi@gmail.com"],
        context={
            "user_name": "Vasista",
            "otp": "12345"
        }
    )
    """
    try:
        email_template = EmailTemplate.objects.get(name=template_name)
        email_config = EmailConfiguration.objects.first()

        # Dynamically render subject, title, main_content, footer_content
        rendered_subject = Template(email_template.subject).render(Context(context))
        rendered_title = Template(email_template.title).render(Context(context))
        rendered_main_content = Template(email_template.main_content).render(Context(context))
        rendered_footer_block = Template(email_template.footer_content).render(Context(context)) if email_template.footer_content else ""

        # Final template context for rendering the base_email.html
        template_context = {
            "subject": rendered_subject,
            "title": rendered_title,
            "main_content": rendered_main_content,
            "footer_block": rendered_footer_block,

            # From EmailConfiguration
            "header_content": email_config.header_content,
            "footer_content": email_config.footer_content,
            "company_name": email_config.company_name,
            "company_logo_url": email_config.company_logo_url,
            "contact_email": email_config.contact_email,
            "copy_right_notice": email_config.copy_right_notice,
        }

        # Include any additional context (optional)
        template_context.update(context)

        html_content = render_to_string("base_email.html", template_context)
        text_content = f"{rendered_title}\n{rendered_main_content}"

        email = EmailMultiAlternatives(rendered_subject, text_content, settings.EMAIL_HOST_USER, recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.send()

        return True, "Email sent successfully"

    except EmailTemplate.DoesNotExist:
        return False, f"EmailTemplate with name '{template_name}' not found"
    except EmailConfiguration.DoesNotExist:
        return False, "No EmailConfiguration found"
    except Exception as e:
        return False, str(e)
    
def extract_hashtags(text):
    """Extracts hashtags from the given text"""
    return set(re.findall(r"#(\w+)", text))


def handle_hashtags(post):
    hashtag_text = f"{post.title} {post.caption} {post.content}"
    hashtags = extract_hashtags(hashtag_text)

    # Clear existing hashtags
    post.hashtags.clear()

    for tag in hashtags:
        hashtag_obj, created = Hashtag.objects.get_or_create(name=tag.lower())
        post.hashtags.add(hashtag_obj)

def get_actual_user(obj):
    """
    Returns the Django User object from a Profile or Organization-based object.
    """
    if hasattr(obj, 'user') and obj.user:
        return obj.user
    elif hasattr(obj, 'organization') and hasattr(obj.organization, 'user'):
        return obj.organization.user
    return None

def handle_art_styles(post, art_styles):
    """
    Handles art styles for a post:
    - Normalizes each art style (lowercase for storage, slugified)
    - Creates ArtType if it doesn't exist
    - Links the ArtType objects to the post
    """

    if not art_styles:
        post.art_types.clear()
        return

    # Normalize input (string -> list)
    if isinstance(art_styles, str):
        art_styles = [s.strip() for s in art_styles.split(",") if s.strip()]
    elif isinstance(art_styles, list):
        art_styles = [s.strip() for s in art_styles if isinstance(s, str) and s.strip()]
    else:
        art_styles = []

    # Normalize names (store lowercase but can display Title Case elsewhere)
    normalized_styles = [s.lower() for s in art_styles]

    # Clear existing art types first
    post.art_types.clear()

    # Get or create each ArtType and link it
    for style in normalized_styles:
        art_type, _ = ArtType.objects.get_or_create(
            name=style
        )
        post.art_types.add(art_type)
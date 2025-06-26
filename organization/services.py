from core.services import send_custom_email
from organization.utils import generate_otp

def send_register_otp_to_email(email):
    """
    Sends an OTP to the specified email address using send_custom_email function.
    
    Args:
        email (str): The email to send the OTP to.
    
    Returns:
        tuple: A tuple containing a boolean indicating success (True/False) 
               and either a success message or an error message.
    
    Process:
        - Generates a 4-digit OTP.
        - Stores the OTP in the cache for 15 minutes.
        - Sends the OTP using the send_custom_email function.
        - Handles any exceptions and returns appropriate error messages.
    """
    try:
        otp = generate_otp(email)
        # Extract name from email (before '@')
        name = email.split('@')[0] if '@' in email else email

        # Send email
        subject = "OTP Verification"
        text_content = f"DXB OTP verification is: {otp}"
        template_address = "organization_register.html"
        context = {
            'otp': otp,
            'name': name
        }
        status, message = send_custom_email(
            subject=subject, text_content=text_content, template_address=template_address, context=context,
            recipient_list=[email]
        )
        if status:
            return True, 'success'
        else:
            return False, message
    except Exception as e:
        return False, str(e)


def send_forgot_otp_to_email(email):
    """
    Sends an OTP to the specified email address using send_custom_email function.
    
    Args:
        email (str): The email to send the OTP to.
    
    Returns:
        tuple: A tuple containing a boolean indicating success (True/False) 
               and either a success message or an error message.
    
    Process:
        - Generates a 4-digit OTP.
        - Stores the OTP in the cache for 15 minutes.
        - Sends the OTP using the send_custom_email function.
        - Handles any exceptions and returns appropriate error messages.
    """
    try:
        otp = generate_otp(email)
        
        # Send email
        subject = "OTP Verification"
        text_content = f"DXB OTP verification is: {otp}"
        template_address = "organization_forgot.html"
        context = {
            'otp':otp
        }
        status, message = send_custom_email(
            subject=subject, text_content=text_content, template_address=template_address, context=context,
            recipient_list=[email]
            )
        if status:
            return True, 'success'
        else:
            return False, message
    except Exception as e:
        return False, str(e)

"""Email service for sending OTP and other notifications"""

import threading
from django.core.mail import send_mail
from django.conf import settings
from core.utils import generate_otp
from authentication.models import OTP

def send_email_thread(subject, message, from_email, recipient_list, fail_silently=False):
    """Execute send_mail in a separate thread to avoid blocking response"""
    try:
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=fail_silently,
        )
    except Exception as e:
        print(f"Error sending email in thread: {e}")

def send_otp_email(user):
    """
    Generate and send OTP to user email (Async)
    Returns the OTP instance
    """
    # Generate OTP
    otp_code = generate_otp()
    
    # Create OTP record
    otp_instance = OTP.objects.create(
        user=user,
        otp=otp_code
    )
    
    # Send email
    subject = 'Neworkx - Email Verification Code'
    message = f'''
    Hello {user.full_name},
    
    Your verification code is: {otp_code}
    
    This code will expire in {settings.OTP_VALIDITY_DURATION} minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    Neworkx Team
    '''
    
    # Send in background thread
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email]),
        kwargs={'fail_silently': False}
    ).start()
    
    return otp_instance


def send_password_reset_email(user, reset_link):
    """Send password reset email to user (Async)"""
    
    subject = 'Neworkx - Password Reset Request'
    message = f'''
    Hello {user.full_name},
    
    You requested to reset your password. Click the link below to reset it:
    
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Neworkx Team
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_payment_receipt_email(user, payment):
    """Send payment confirmation email (Async)"""
    
    subject = 'Neworkx - Payment Receipt'
    message = f'''
    Hello {user.full_name},
    
    Thank you for your payment!
    
    Receipt Number: {payment.receipt_number}
    Amount: ${payment.amount} {payment.currency}
    Status: {payment.status}
    Date: {payment.created_at.strftime('%Y-%m-%d %H:%M')}
    
    You can now access all platform features.
    
    Best regards,
    Neworkx Team
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_welcome_email(user):
    """Send welcome email after successful registration (Async)"""
    
    subject = 'Welcome to Neworkx!'
    message = f'''
    Hello {user.full_name},
    
    Welcome to Neworkx! We're excited to have you on board.
    
    Your account has been successfully created. You can now access:
    - Job search and applications
    - Training programs
    - Resume builder
    - And much more!
    
    Log in to get started: {settings.DOMAIN_URL}/login
    
    Best regards,
    The Neworkx Team
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_interview_invitation_email(applicant, job, employer, interview):
    """Send interview invitation email to applicant"""
    
    # Format date and time
    interview_date = interview.scheduled_date.strftime('%A, %B %d, %Y')
    interview_time = interview.scheduled_time.strftime('%I:%M %p')
    
    # Build meeting details
    meeting_details = ""
    if interview.meeting_link:
        meeting_details = f"Meeting Link: {interview.meeting_link}"
    elif interview.location:
        meeting_details = f"Location: {interview.location}"
    else:
        meeting_details = "Meeting details will be shared separately."
    
    subject = f'Interview Invitation - {job.title} at {employer.company_name}'
    message = f'''
    Hello {applicant.full_name},
    
    Great news! You have been invited for an interview for the position of {job.title} at {employer.company_name}.
    
    JOB DETAILS:
    • Position: {job.title}
    • Company: {employer.company_name}
    • Location: {job.location}
    • Employment Type: {job.get_employment_type_display()}
    
    INTERVIEW DETAILS:
    • Date: {interview_date}
    • Time: {interview_time}
    • Duration: {interview.duration_minutes} minutes
    • {meeting_details}
    
    {f"Additional Notes: {interview.notes}" if interview.notes else ""}
    
    Please make sure you are available at the scheduled time. If you have any questions or need to reschedule, please contact the employer.
    
    We wish you the best of luck with your interview!
    
    Best regards,
    Neworkx Team
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [applicant.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_rejection_email(applicant, job, employer):
    """Send application rejection email to applicant"""
    
    subject = f'Application Update - {job.title} at {employer.company_name}'
    message = f'''
    Hello {applicant.full_name},
    
    Thank you for your interest in the {job.title} position at {employer.company_name}.
    
    After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.
    
    JOB DETAILS:
    • Position: {job.title}
    • Company: {employer.company_name}
    • Location: {job.location}
    
    We appreciate the time you invested in applying and wish you the best in your job search. We encourage you to apply for future openings that match your skills and experience.
    
    Best regards,
    {employer.company_name} Team
    Neworkx
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [applicant.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_hiring_email(applicant, job, employer, hiring_details):
    """Send hiring congratulations email to applicant"""
    
    start_date = hiring_details.get('start_date', 'TBD')
    joining_time = hiring_details.get('joining_time', '')
    hiring_notes = hiring_details.get('hiring_notes', '')
    
    # Format date if provided
    if start_date != 'TBD':
        start_date = start_date.strftime('%A, %B %d, %Y')
    
    # Format time if provided
    time_info = f" at {joining_time.strftime('%I:%M %p')}" if joining_time else ""
    
    # Format salary info if available
    salary_info = ""
    if job.salary_min and job.salary_max:
        salary_info = f"• Salary Range: ${job.salary_min} - ${job.salary_max}"
    
    # Format additional info
    additional_info = ""
    if hiring_notes:
        additional_info = "ADDITIONAL INFORMATION:\n    " + hiring_notes + "\n    \n    "
    
    subject = f'Congratulations! You\'re Hired - {job.title} at {employer.company_name}'
    message = f'''
    Hello {applicant.full_name},
    
    Congratulations! We are pleased to offer you the position of {job.title} at {employer.company_name}.
    
    JOB DETAILS:
    • Position: {job.title}
    • Company: {employer.company_name}
    • Location: {job.location}
    • Employment Type: {job.get_employment_type_display()}
    {salary_info}
    
    START DATE:
    • Date: {start_date}{time_info}
    
    {additional_info}We are excited to have you join our team! Please reach out if you have any questions.
    
    Welcome aboard!
    
    Best regards,
    {employer.company_name} Team
    Neworkx
    '''
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [applicant.email]),
        kwargs={'fail_silently': False}
    ).start()


def send_contact_form_to_admin(contact_message):
    """Send contact form submission notification to admin"""
    
    # Determine sender info
    if contact_message.user:
        sender_name = contact_message.user.full_name
        sender_email = contact_message.user.email
    else:
        sender_name = contact_message.name
        sender_email = contact_message.email
    
    # Format phone info
    phone_info = f"Phone: {contact_message.phone}" if contact_message.phone else "Phone: Not provided"
    
    # Format subject info
    subject_info = contact_message.subject if contact_message.subject else "No subject provided"
    
    subject = f'New Contact Form Submission from {sender_name}'
    message = f'''
    New Contact Form Submission
    
    FROM:
    • Name: {sender_name}
    • Email: {sender_email}
    • {phone_info}
    
    SUBJECT:
    {subject_info}
    
    MESSAGE:
    {contact_message.message}
    
    ---
    Submission ID: {contact_message.id}
    Submitted at: {contact_message.created_at.strftime('%Y-%m-%d %H:%M:%S')}
    
    This message was sent via the Neworkx contact form.
    '''
    
    # Admin email
    admin_email = 'jamilhossain3251@gmail.com'
    
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [admin_email]),
        kwargs={'fail_silently': False}
    ).start()

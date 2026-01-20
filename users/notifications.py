"""
Notification helper functions to create notifications from various events.
Call these functions from views when relevant events occur.
"""
from django.contrib.auth import get_user_model
from .notification_models import Notification

User = get_user_model()


def get_admin_users():
    """Get all superuser/admin users to notify"""
    return User.objects.filter(is_superuser=True, is_active=True)


# ==================== USER (AGENCY) NOTIFICATIONS ====================

def notify_training_enrolled(user, training_program):
    """Notify user they enrolled in a training"""
    Notification.objects.create(
        recipient=user,
        notification_type='training_enrolled',
        title='Training Enrolled',
        message=f'You have enrolled in "{training_program.name}"',
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
        }
    )


def notify_certificate_uploaded(user, training_program):
    """Notify user their certificate was uploaded"""
    Notification.objects.create(
        recipient=user,
        notification_type='certificate_uploaded',
        title='Certificate Uploaded',
        message=f'Your certificate for "{training_program.name}" is pending verification',
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
        }
    )


def notify_certificate_verified(user, training_program):
    """Notify user their certificate was verified"""
    Notification.objects.create(
        recipient=user,
        notification_type='certificate_verified',
        title='Certificate Verified ✓',
        message=f'Your certificate for "{training_program.name}" has been verified',
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
        }
    )


def notify_certificate_rejected(user, training_program, reason=''):
    """Notify user their certificate was rejected"""
    msg = f'Your certificate for "{training_program.name}" was rejected'
    if reason:
        msg += f'. Reason: {reason}'
    
    Notification.objects.create(
        recipient=user,
        notification_type='certificate_rejected',
        title='Certificate Rejected',
        message=msg,
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
            'reason': reason,
        }
    )


def notify_job_applied(user, job):
    """Notify user they applied to a job"""
    Notification.objects.create(
        recipient=user,
        notification_type='job_applied',
        title='Application Submitted',
        message=f'You applied for "{job.title}" at {job.employer.company_name}',
        data={
            'job_id': str(job.id),
            'job_title': job.title,
            'company': job.employer.company_name,
        }
    )


def notify_application_status_change(user, job, new_status, notes=''):
    """Notify user about application status change"""
    status_map = {
        'interview_scheduled': ('application_interview', 'Interview Scheduled', f'You have an interview scheduled for "{job.title}"'),
        'hired': ('application_hired', 'Congratulations! 🎉', f'You have been hired for "{job.title}"'),
        'rejected': ('application_rejected', 'Application Update', f'Your application for "{job.title}" was not selected'),
        'offer_received': ('application_hired', 'Offer Received', f'You received an offer for "{job.title}"'),
    }
    
    if new_status in status_map:
        notif_type, title, message = status_map[new_status]
        if notes:
            message += f'. Note: {notes}'
        
        Notification.objects.create(
            recipient=user,
            notification_type=notif_type,
            title=title,
            message=message,
            data={
                'job_id': str(job.id),
                'job_title': job.title,
                'status': new_status,
            }
        )


def notify_welcome(user, user_type='general'):
    """Send welcome notification after signup"""
    Notification.objects.create(
        recipient=user,
        notification_type='welcome',
        title='Welcome to RB Wood!',
        message='Your account is all set up. Start exploring jobs and training programs!',
        data={'user_type': user_type}
    )


# ==================== TRAINER NOTIFICATIONS ====================

def notify_trainer_new_enrollment(trainer_user, trainee, training_program):
    """Notify trainer someone enrolled in their training"""
    Notification.objects.create(
        recipient=trainer_user,
        notification_type='new_enrollment',
        title='New Enrollment',
        message=f'{trainee.full_name} enrolled in "{training_program.name}"',
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
            'trainee_id': str(trainee.id),
            'trainee_name': trainee.full_name,
        }
    )


def notify_trainer_certificate_pending(trainer_user, trainee, training_program):
    """Notify trainer a certificate needs verification"""
    Notification.objects.create(
        recipient=trainer_user,
        notification_type='certificate_pending',
        title='Certificate Awaiting Verification',
        message=f'{trainee.full_name} uploaded a certificate for "{training_program.name}"',
        data={
            'training_id': str(training_program.id),
            'training_name': training_program.name,
            'trainee_id': str(trainee.id),
            'trainee_name': trainee.full_name,
        }
    )


# ==================== EMPLOYER NOTIFICATIONS ====================

def notify_employer_new_application(employer_user, applicant, job):
    """Notify employer of new job application"""
    Notification.objects.create(
        recipient=employer_user,
        notification_type='new_application',
        title='New Application',
        message=f'{applicant.full_name} applied for "{job.title}"',
        data={
            'job_id': str(job.id),
            'job_title': job.title,
            'applicant_id': str(applicant.id),
            'applicant_name': applicant.full_name,
        }
    )


# ==================== ADMIN NOTIFICATIONS ====================

def notify_admin_new_registration(user, user_type):
    """Notify admins of new pending registration"""
    type_map = {
        'training_provider': ('new_trainer_pending', 'New Trainer Registration'),
        'employer': ('new_employer_pending', 'New Employer Registration'),
        'agency': ('new_agency_pending', 'New Agency Registration'),
        'general': ('new_user_signup', 'New Job Seeker Registration'),
        'referred': ('new_user_signup', 'New Referred User Registration'),
    }
    
    if user_type in type_map:
        notif_type, title = type_map[user_type]
        
        # Determine message suffix based on user type
        if user_type in ['general', 'referred']:
            suffix = "signed up"
        else:
            suffix = "registered - pending approval"
            
        for admin in get_admin_users():
            Notification.objects.create(
                recipient=admin,
                notification_type=notif_type,
                title=title,
                message=f'{user.full_name} ({user.email}) {suffix}',
                data={
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'user_name': user.full_name,
                    'user_type': user_type,
                }
            )


def notify_admin_user_paid(user, user_type):
    """Notify admins when user completes payment"""
    notif_type = 'referred_user_paid' if user_type == 'referred' else 'general_user_paid'
    title = 'User Completed Payment'
    
    for admin in get_admin_users():
        Notification.objects.create(
            recipient=admin,
            notification_type=notif_type,
            title=title,
            message=f'{user.full_name} ({user_type} user) completed their payment',
            data={
                'user_id': str(user.id),
                'user_email': user.email,
                'user_type': user_type,
            }
        )


def notify_admin_new_job_posted(job):
    """Notify admins when employer posts a new job"""
    for admin in get_admin_users():
        Notification.objects.create(
            recipient=admin,
            notification_type='new_job_posted',
            title='New Job Posted',
            message=f'"{job.title}" posted by {job.employer.company_name}',
            data={
                'job_id': str(job.id),
                'job_title': job.title,
                'employer': job.employer.company_name,
            }
        )


def notify_admin_new_training_created(training_program):
    """Notify admins when trainer creates new training"""
    for admin in get_admin_users():
        Notification.objects.create(
            recipient=admin,
            notification_type='new_training_created',
            title='New Training Created',
            message=f'"{training_program.name}" created by {training_program.provider.user.full_name}',
            data={
                'training_id': str(training_program.id),
                'training_name': training_program.name,
                'provider': training_program.provider.user.full_name,
            }
        )


def notify_account_approved(user, user_type):
    """Notify user their account has been approved/verified"""
    Notification.objects.create(
        recipient=user,
        notification_type='account_approved',
        title='Account Verified 🎉',
        message=f'Your {user_type} account has been verified. You now have full access.',
        data={
            'user_type': user_type,
            'status': 'verified'
        }
    )


def notify_account_banned(user, user_type, reason=''):
    """Notify user their account has been suspended/banned"""
    message = f'Your {user_type} account has been suspended'
    if reason:
        message += f'. Reason: {reason}'
        
    Notification.objects.create(
        recipient=user,
        notification_type='account_suspended',
        title='Account Suspended ⚠️',
        message=message,
        data={
            'user_type': user_type,
            'status': 'banned',
            'reason': reason
        }
    )

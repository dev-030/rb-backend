"""Custom permission classes for role-based access control"""

from rest_framework import permissions


class IsGeneralUser(permissions.BasePermission):
    """Permission for general job seekers"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'general'
        )


class IsReferredUser(permissions.BasePermission):
    """Permission for court-referred users"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'agency_referred'
        )


class IsJobSeeker(permissions.BasePermission):
    """Permission for any job seeker (general or referred)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['general', 'agency_referred']
        )


class IsEmployer(permissions.BasePermission):
    """Permission for employers"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'employer'
        )


class IsVerifiedEmployer(permissions.BasePermission):
    """Permission for verified employers only"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            self.message = "Authentication required."
            return False
        
        if request.user.user_type != 'employer':
            self.message = "This action is only available to employer accounts."
            return False
        
        try:
            employer_profile = request.user.employer_profile
            if employer_profile.status == 'verified':
                return True
            elif employer_profile.status == 'pending':
                self.message = "Your employer account is pending verification. Please wait for admin approval."
                return False
            elif employer_profile.status == 'banned':
                self.message = "Your employer account has been banned. Please contact support for assistance."
                return False
            else:
                self.message = f"Your employer account status is '{employer_profile.status}'. Verification required."
                return False
        except AttributeError:
            self.message = "Employer profile not found. Please complete your employer registration."
            return False
        except Exception as e:
            self.message = "An error occurred while checking your employer status."
            return False



class IsTrainingProvider(permissions.BasePermission):
    """Permission for training providers"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'training_provider'
        )


class IsVerifiedTrainingProvider(permissions.BasePermission):
    """Permission for verified training providers only"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            self.message = "Authentication required."
            return False
        
        if request.user.user_type != 'training_provider':
            self.message = "This action is only available to training provider accounts."
            return False
        
        try:
            trainer_profile = request.user.trainer_profile
            if trainer_profile.status == 'verified':
                return True
            elif trainer_profile.status == 'pending':
                self.message = "Your training provider account is pending verification. Please wait for admin approval."
                return False
            elif trainer_profile.status == 'banned':
                self.message = "Your training provider account has been banned. Please contact support for assistance."
                return False
            else:
                self.message = f"Your training provider account status is '{trainer_profile.status}'. Verification required."
                return False
        except AttributeError:
            self.message = "Training provider profile not found. Please complete your registration."
            return False
        except Exception as e:
            self.message = "An error occurred while checking your training provider status."
            return False


class IsAgency(permissions.BasePermission):
    """Permission for agencies"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'agency'
        )


class IsVerifiedAgency(permissions.BasePermission):
    """Permission for verified agencies only"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            self.message = "Authentication required."
            return False
        
        if request.user.user_type != 'agency':
            self.message = "This action is only available to agency accounts."
            return False
        
        try:
            agency_profile = request.user.agency_profile
            if agency_profile.status == 'verified':
                return True
            elif agency_profile.status == 'pending':
                self.message = "Your agency account is pending verification. Please wait for admin approval."
                return False
            elif agency_profile.status == 'banned':
                self.message = "Your agency account has been banned. Please contact support for assistance."
                return False
            else:
                self.message = f"Your agency account status is '{agency_profile.status}'. Verification required."
                return False
        except AttributeError:
            self.message = "Agency profile not found. Please complete your registration."
            return False
        except Exception as e:
            self.message = "An error occurred while checking your agency status."
            return False


class IsAdmin(permissions.BasePermission):
    """Permission for super admin"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'admin' and
            request.user.is_staff
        )


class IsPaidUser(permissions.BasePermission):
    """Permission for users who have completed payment"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        user_type = request.user.user_type
        
        try:
            if user_type == 'general':
                return request.user.general_profile.has_paid
            elif user_type == 'agency_referred':
                return request.user.referred_profile.has_paid
            else:
                return True  # Non job-seeker roles don't need payment
        except:
            return False

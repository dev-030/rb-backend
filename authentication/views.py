"""Authentication views for registration, login, OTP verification, and password reset"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .tokens import CustomRefreshToken

from .serializers import (
    RegisterSerializer, OTPVerifySerializer, LoginSerializer,
    UserProfileSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    ChangePasswordSerializer
)
from .email_service import send_otp_email, send_welcome_email
from authentication.models import OTP
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from users.notifications import notify_admin_new_registration


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Check for pending agency cases
        try:
            from agency.models import AgencyCaseLoad
            from users.models import ReferredUser, CaseAssignment
            
            pending_cases = AgencyCaseLoad.objects.filter(email=user.email, is_registered=False)
            
            for pending_case in pending_cases:
                # Link user
                pending_case.matched_user = user
                pending_case.is_registered = True
                pending_case.save()
                
                # Create ReferredUser profile
                referred_profile, _ = ReferredUser.objects.get_or_create(
                    user=user,
                    defaults={
                        'phone_number': '',
                        'court_name': pending_case.court_name,
                        'case_id': pending_case.case_id
                    }
                )
                
                # Assign Case
                CaseAssignment.objects.get_or_create(
                    referred_user=referred_profile,
                    agency=pending_case.agency,
                    defaults={
                        'case_id': pending_case.case_id,
                        'court_date': pending_case.court_date,
                        'compliance_status': pending_case.status if pending_case.status in ['on_track', 'delayed', 'non_compliant', 'completed'] else 'on_track'
                    }
                )
        except Exception as e:
            # Don't fail registration if linking fails
            print(f"Error linking pending cases: {e}")
        
        # Send OTP for email verification
        try:
            send_otp_email(user)
        except Exception as e:
            print(f"Error sending OTP email: {e}")
            
        # Notify admins about new registration
        try:
            # Notify for all user types defined in notification system
            notify_admin_new_registration(user, user.user_type)
        except Exception as e:
            print(f"Error notifying admin: {e}")
        
        return Response({
            "message": "Registration successful. Please check your email for verification code.",
            "email": user.email,
            "user_type": user.user_type
        }, status=status.HTTP_201_CREATED)


class SendOTPView(APIView):
    """Resend OTP to user email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete old OTPs
        user.otps.all().delete()
        
        # Send new OTP
        try:
            send_otp_email(user)
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Failed to send OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    """Verify OTP and activate user account"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        otp_instance = serializer.validated_data['otp_instance']
        
        # Activate user
        user.is_active = True
        user.save()
        
        # Delete used OTP
        otp_instance.delete()
        
        # Send welcome email
        try:
            send_welcome_email(user)
        except:
            pass
        
        # Generate JWT tokens for automatic login
        refresh = CustomRefreshToken.for_user(user)
        
        return Response({
            "message": "Email verified successfully. You can now log in.",
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Use custom token to include user_type and email in payload
        refresh = CustomRefreshToken.for_user(user)
        
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """User logout - blacklist refresh token"""
    permission_classes =[IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update current user profile"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PasswordResetRequestView(APIView):
    """Request password reset - sends OTP to email and returns a reset token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        import jwt
        from datetime import timedelta
        from django.utils import timezone
        from django.conf import settings
        
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Delete old OTPs
        user.otps.all().delete()
        
        # Send OTP
        try:
            send_otp_email(user)
            
            # Generate JWT token for OTP verification
            payload = {
                'user_id': str(user.id),
                'purpose': 'password_reset',
                'exp': timezone.now() + timedelta(minutes=15),
                'iat': timezone.now()
            }
            reset_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            
            return Response({
                "message": "Password reset OTP sent to your email",
                "reset_token": reset_token
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": "Failed to send OTP"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyResetOtpView(APIView):
    """Verify OTP for password reset - returns a new token with password hash"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        import jwt
        import hashlib
        from datetime import timedelta
        from django.utils import timezone
        from django.conf import settings
        
        reset_token = request.data.get('reset_token')
        otp = request.data.get('otp')
        
        if not reset_token or not otp:
            return Response({
                "error": "Reset token and OTP are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify the initial reset token
            payload = jwt.decode(reset_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            if payload.get('purpose') != 'password_reset':
                return Response({
                    "error": "Invalid token purpose"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.get(id=payload['user_id'], is_active=True)
        except (jwt.PyJWTError, User.DoesNotExist):
            return Response({
                "error": "Invalid or expired token"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify OTP
        try:
            otp_instance = user.otps.filter(otp=otp).latest('created_at')
            from core.utils import is_otp_valid
            
            if not is_otp_valid(otp_instance):
                return Response({
                    "error": "OTP has expired"
                }, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({
                "error": "Invalid OTP"
            }, status=status.HTTP_400_BAD_REQUEST)
        
       # Generate password fingerprint for security
        password_fingerprint = hashlib.sha256(user.password.encode()).hexdigest()[:12]
        
        # Create new token with password hash
        new_payload = {
            'user_id': str(user.id),
            'purpose': 'password_reset_confirmed',
            'security_hash': password_fingerprint,
            'exp': timezone.now() + timedelta(minutes=15),
            'iat': timezone.now()
        }
        new_reset_token = jwt.encode(new_payload, settings.SECRET_KEY, algorithm='HS256')
        
        # Delete the used OTP
        otp_instance.delete()
        
        return Response({
            "message": "OTP verified successfully",
            "reset_token": new_reset_token
        }, status=status.HTTP_200_OK)


class SetNewPasswordView(APIView):
    """Set new password using verified reset token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        import jwt
        import hashlib
        from django.conf import settings
        
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        
        if not reset_token or not new_password:
            return Response({
                "error": "Reset token and new password are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify the token
            payload = jwt.decode(reset_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            if payload.get('purpose') != 'password_reset_confirmed':
                return Response({
                    "error": "Invalid token purpose"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.get(id=payload['user_id'], is_active=True)
            
            # Verify password hasn't changed since OTP verification
            current_fingerprint = hashlib.sha256(user.password.encode()).hexdigest()[:12]
            token_fingerprint = payload.get('security_hash')
            
            if token_fingerprint != current_fingerprint:
                return Response({
                    "error": "This reset link has already been used. Please request a new one."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            # Delete all remaining OTPs
            user.otps.all().delete()
            
            return Response({
                "message": "Password reset successful. You can now log in with your new password."
            }, status=status.HTTP_200_OK)
            
        except (jwt.PyJWTError, User.DoesNotExist):
            return Response({
                "error": "Invalid or expired token"
            }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change password for authenticated users"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Set the new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            "message": "Password changed successfully"
        }, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    """
    Google Login View
    Verifies the ID token from the client and logs in/creates the user.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('id_token')
        if not token:
            return Response({'error': 'ID token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the token
            # We don't specify the audience (client_id) here to allow any valid google token 
            # (since we might have Android, iOS, and Web client IDs).
            # In a stricter environment, we would validate against our specific client IDs.
            id_info = id_token.verify_oauth2_token(token, google_requests.Request())

            email = id_info.get('email')
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')
            
            if not email:
                return Response({'error': 'Email not found in token'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if user exists
            try:
                user = User.objects.get(email=email)
                # Fix for existing google users with no user_type
                if not user.user_type:
                    user.user_type = 'general'
                    user.save()
            except User.DoesNotExist:
                # Create a new user
                # We need a random password
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(20))
                
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=True, # Google users are verified by default
                    user_type='general' # Default to general job seeker
                )
                
                # Check for pending agency cases (Reusing logic from RegisterView)
                try:
                    from agency.models import AgencyCaseLoad
                    from users.models import ReferredUser, CaseAssignment
                    
                    pending_cases = AgencyCaseLoad.objects.filter(email=user.email, is_registered=False)
                    
                    for pending_case in pending_cases:
                        # Link user
                        pending_case.matched_user = user
                        pending_case.is_registered = True
                        pending_case.save()
                        
                        # Create ReferredUser profile
                        referred_profile, _ = ReferredUser.objects.get_or_create(
                            user=user,
                            defaults={
                                'phone_number': '',
                                'court_name': pending_case.court_name,
                                'case_id': pending_case.case_id
                            }
                        )
                        
                        # Assign Case
                        CaseAssignment.objects.get_or_create(
                            referred_user=referred_profile,
                            agency=pending_case.agency,
                            defaults={
                                'case_id': pending_case.case_id,
                                'court_date': pending_case.court_date,
                                'compliance_status': pending_case.status if pending_case.status in ['on_track', 'delayed', 'non_compliant', 'completed'] else 'on_track'
                            }
                        )
                    
                    # If no pending cases matched, verify if we should create a default ReferredUser profile?
                    # The RegisterView only creates it if pending cases exist. 
                    # But often we want a profile for every user. 
                    # Assuming standard flow where new users might be job seekers.
                    if not pending_cases.exists():
                         # Check if we need to create a default profile for job seeker
                         # For now, let's leave it as minimal user as per RegisterView logic
                         pass

                except Exception as e:
                    print(f"Error linking pending cases: {e}")

            # Login successful, generate tokens
            refresh = CustomRefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'id': user.id
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({'error': f'Invalid token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print(e)
            return Response({'error': 'Authentication failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
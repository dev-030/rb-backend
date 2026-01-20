"""Custom JWT token to include user_type and email in the payload"""

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken


class CustomAccessToken(AccessToken):
    """Custom AccessToken with user_type, email, and full_name claims"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @classmethod
    def for_user(cls, user):
        """Create access token with custom claims"""
        token = super().for_user(user)
        token['user_type'] = user.user_type
        token['email'] = user.email
        token['full_name'] = user.full_name
        return token


class CustomRefreshToken(RefreshToken):
    """Custom RefreshToken that generates CustomAccessToken with user claims"""
    
    # Specify that we want to use our custom access token
    access_token_class = CustomAccessToken
    
    @classmethod
    def for_user(cls, user):
        """
        Create a refresh token for the given user with custom claims
        
        Args:
            user: The user object
            
        Returns:
            CustomRefreshToken instance
        """
        token = super().for_user(user)
        
        # Add custom claims to the refresh token payload
        token['user_type'] = user.user_type
        token['email'] = user.email
        token['full_name'] = user.full_name
        
        # Store user for access token generation
        token._user = user
        
        return token
    
    @property
    def access_token(self):
        """
        Generate access token with custom claims
        """
        # Create the access token using our custom class
        access = self.access_token_class()
        access.set_exp(from_time=self.current_time)

        # Copy user_id from refresh token
        access['user_id'] = self['user_id']
        
        # Add our custom claims
        if hasattr(self, '_user'):
            access['user_type'] = self._user.user_type
            access['email'] = self._user.email
            access['full_name'] = self._user.full_name
        else:
            # Fallback: try to get from refresh token payload
            access['user_type'] = self.get('user_type')
            access['email'] = self.get('email')
            access['full_name'] = self.get('full_name')

        return access

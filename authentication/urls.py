from django.urls import path
from .views import (
    RegisterView, SendOTPView, VerifyOTPView, LoginView, LogoutView,
    ProfileView, PasswordResetRequestView, VerifyResetOtpView, SetNewPasswordView,
    ChangePasswordView, GoogleLoginView, CompleteProfileView, AppleLoginView
)
from .payment_views import (
    CreateCheckoutSessionView, StripeWebhookView,
    PaymentHistoryView, DownloadReceiptView
)
from rest_framework_simplejwt.views import ( TokenObtainPairView, TokenRefreshView )




urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('google/', GoogleLoginView.as_view(), name='google_login'),
    path('apple/', AppleLoginView.as_view(), name='apple_login'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete_profile'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-verify-otp/', VerifyResetOtpView.as_view(), name='verify_reset_otp'),
    path('password-reset-confirm/', SetNewPasswordView.as_view(), name='set_new_password'),
    
    # Payment - Stripe Checkout Session
    path('payment/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create_checkout_session'),
    path('payment/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('payment/history/', PaymentHistoryView.as_view(), name='payment_history'),
    path('payment/receipt/<uuid:payment_id>/', DownloadReceiptView.as_view(), name='download_receipt'),
]
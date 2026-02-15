"""Payment processing views with Stripe Checkout Session integration"""

import stripe
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse

from users.models import Payment, TransactionLog
from .payment_serializers import PaymentSerializer, CheckoutSessionSerializer
from .email_service import send_payment_receipt_email
from core.permissions import IsJobSeeker

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(APIView):
    """Create Stripe Checkout Session for registration fee"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get amount (default to registration fee)
        amount = serializer.validated_data.get('amount', settings.REGISTRATION_FEE)
        description = serializer.validated_data.get('description', 'Registration Fee')
        
        try:
            # Create payment record first
            payment = Payment.objects.create(
                user=request.user,
                amount=amount,
                currency='usd',
                payment_method='stripe',
                status='pending',
                description=description
            )
            
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                # payment_method_types=['card', 'klarna'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(float(amount) * 100),  # Convert to cents
                        'product_data': {
                            'name': description,
                            'description': f'One-time registration fee for {request.user.full_name}',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
                customer_email=request.user.email,
                metadata={
                    'payment_id': str(payment.id),
                    'user_id': str(request.user.id),
                    'user_email': request.user.email,
                    'user_type': request.user.user_type
                }
            )
            
            # Update payment with checkout session ID
            payment.stripe_checkout_session_id = checkout_session.id
            payment.save()
            
            # Log transaction
            TransactionLog.objects.create(
                payment=payment,
                event_type='checkout_session_created',
                details={'session_id': checkout_session.id}
            )
            
            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'payment_id': str(payment.id),
                'amount': float(amount)
            }, status=status.HTTP_200_OK)
            
        except stripe.error.StripeError as e:
            # Clean up payment record if Stripe fails
            if payment:
                payment.delete()
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Handle Stripe webhook events for Checkout Session"""
    permission_classes = []
    
    def post(self, request):
        print("🔔 Webhook received..........................................")
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        # Debug logging
        print(f"📝 Webhook Secret configured: {bool(settings.STRIPE_WEBHOOK_SECRET)}")
        print(f"📝 Signature header present: {bool(sig_header)}")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            print(f"❌ Invalid payload: {e}")
            print(f"📄 Payload preview: {payload[:200]}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            print(f"❌ Invalid signature: {e}")
            print(f"🔑 Webhook secret is set: {bool(settings.STRIPE_WEBHOOK_SECRET)}")
            print(f"🔑 Webhook secret length: {len(settings.STRIPE_WEBHOOK_SECRET) if settings.STRIPE_WEBHOOK_SECRET else 0}")
            print(f"🔑 Signature header: {sig_header[:50] if sig_header else 'None'}...")
            return HttpResponse(status=400)
        
        print(f"✅ Received event: {event['type']}")
        
        # Handle checkout session completed event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            try:
                # DEBUG LOGGING
                print(f"ℹ️ Processing checkout session: {session.get('id')}")
                print(f"ℹ️ Session object type: {type(session)}")
                metadata = session.get('metadata', {})
                print(f"ℹ️ Session Metadata: {metadata}")
                
                # Get required fields from session
                payment_id = metadata.get('payment_id')
                print(f"ℹ️ Extracted payment_id: {payment_id}")
                
                if not payment_id:
                    print(f"❌ No payment_id in session metadata")
                    return HttpResponse(status=200)
                
                # Find payment record
                try:
                    payment = Payment.objects.get(id=payment_id)
                    print(f"💳 Payment found: ID={payment_id}, Current Status={payment.status}")
                except Payment.DoesNotExist:
                    print(f"❌ Payment not found: {payment_id}")
                    return HttpResponse(status=200)
                
                # Update payment status
                print(f"🔄 Updating payment status from '{payment.status}' to 'succeeded'")
                payment.status = 'succeeded'
                payment.stripe_checkout_session_id = session['id']
                
                # Get receipt URL from payment intent if available
                payment_intent_id = session.get('payment_intent')
                if payment_intent_id:
                    try:
                        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                        latest_charge_id = payment_intent.get('latest_charge')
                        if latest_charge_id:
                            charge = stripe.Charge.retrieve(latest_charge_id)
                            payment.receipt_url = charge.get('receipt_url', '')
                    except Exception as e:
                        print(f"⚠️ Could not retrieve receipt URL: {e}")
                
                payment.generate_receipt_number()
                payment.save()
                print(f"💾 Payment saved successfully: Status={payment.status}, Receipt={payment.receipt_number}\"")
                
                # Verify payment was saved to database
                payment.refresh_from_db()
                print(f"✅ VERIFIED - Payment in DB: ID={payment.id}, Status={payment.status}, Amount=${payment.amount}")
                
                # ✅ UPDATE has_paid STATUS FOR USER
                user = payment.user
                try:
                    if user.user_type == 'general':
                        profile = user.general_profile
                        old_has_paid = profile.has_paid
                        profile.has_paid = True
                        profile.save()
                        profile.refresh_from_db()
                        print(f"✅ Updated has_paid for general user: {user.email}")
                        print(f"   └─ has_paid: {old_has_paid} → {profile.has_paid}")
                    elif user.user_type == 'agency_referred':
                        profile = user.referred_profile
                        old_has_paid = profile.has_paid
                        profile.has_paid = True
                        profile.save()
                        profile.refresh_from_db()
                        print(f"✅ Updated has_paid for court-referred user: {user.email}")
                        print(f"   └─ has_paid: {old_has_paid} → {profile.has_paid}")
                except Exception as e:
                    print(f"⚠️ Could not update has_paid: {e}")
                
                
                # Log transaction
                TransactionLog.objects.create(
                    payment=payment,
                    event_type='checkout_completed',
                    details={
                        'session_id': session['id'],
                        'customer_email': session.get('customer_email'),
                        'amount_total': session['amount_total'],
                        'payment_status': session['payment_status']
                    }
                )
                
                # Send receipt email
                try:
                    send_payment_receipt_email(user, payment)
                    print(f"✅ Receipt email sent to: {user.email}")
                except Exception as e:
                    print(f"⚠️ Failed to send receipt email: {e}")
                
                print(f"✅ Payment completed: ${payment.amount} for {user.email}")
                print(f"=" * 80)
                print(f"📊 ADMIN DASHBOARD SHOULD NOW SHOW:")
                print(f"   Payment ID: {payment.id}")
                print(f"   User: {user.email}")
                print(f"   Amount: ${payment.amount}")
                print(f"   Status: {payment.status} ✅")
                print(f"   Receipt: {payment.receipt_number}")
                print(f"   Has Paid: {profile.has_paid if 'profile' in locals() else 'N/A'} ✅")
                print(f"=" * 80)
                
            except Exception as e:
                print(f"❌ Error processing checkout.session.completed: {e}")
                import traceback
                traceback.print_exc()
                return HttpResponse(status=200)
        
        # Handle checkout session expired (cancelled/timed out)
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            
            try:
                payment_id = session.get('metadata', {}).get('payment_id')
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    payment.status = 'failed'
                    payment.save()
                    
                    TransactionLog.objects.create(
                        payment=payment,
                        event_type='checkout_expired',
                        details={'session_id': session.get('id')}
                    )
                    print(f"⚠️ Checkout session expired for payment: {payment_id}")
            except Payment.DoesNotExist:
                pass
            except Exception as e:
                print(f"❌ Error processing checkout.session.expired: {e}")
        
        # Handle async payments (bank transfers, ACH, etc.) that complete after checkout
        elif event['type'] == 'checkout.session.async_payment_succeeded':
            session = event['data']['object']
            
            try:
                payment_id = session.get('metadata', {}).get('payment_id')
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    print(f"💳 Async payment succeeded: ID={payment_id}")
                    
                    payment.status = 'succeeded'
                    payment.stripe_checkout_session_id = session['id']
                    
                    # Get receipt URL
                    payment_intent_id = session.get('payment_intent')
                    if payment_intent_id:
                        try:
                            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                            latest_charge_id = payment_intent.get('latest_charge')
                            if latest_charge_id:
                                charge = stripe.Charge.retrieve(latest_charge_id)
                                payment.receipt_url = charge.get('receipt_url', '')
                        except Exception as e:
                            print(f"⚠️ Could not retrieve receipt URL: {e}")
                    
                    payment.generate_receipt_number()
                    payment.save()
                    print(f"💾 Async payment saved: Status={payment.status}")
                    
                    # Update has_paid status
                    user = payment.user
                    try:
                        if user.user_type == 'general':
                            profile = user.general_profile
                            profile.has_paid = True
                            profile.save()
                            print(f"✅ Updated has_paid for general user: {user.email}")
                        elif user.user_type == 'agency_referred':
                            profile = user.referred_profile
                            profile.has_paid = True
                            profile.save()
                            print(f"✅ Updated has_paid for court-referred user: {user.email}")
                    except Exception as e:
                        print(f"⚠️ Could not update has_paid: {e}")
                    
                    # Log transaction
                    TransactionLog.objects.create(
                        payment=payment,
                        event_type='async_payment_succeeded',
                        details={'session_id': session.get('id')}
                    )
                    
                    # Send receipt email
                    try:
                        send_payment_receipt_email(user, payment)
                        print(f"✅ Async payment receipt sent to: {user.email}")
                    except Exception as e:
                        print(f"⚠️ Failed to send receipt email: {e}")
                        
            except Payment.DoesNotExist:
                print(f"❌ Payment not found for async payment: {payment_id}")
            except Exception as e:
                print(f"❌ Error processing async_payment_succeeded: {e}")
        
        # Handle async payment failures
        elif event['type'] == 'checkout.session.async_payment_failed':
            session = event['data']['object']
            
            try:
                payment_id = session.get('metadata', {}).get('payment_id')
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    payment.status = 'failed'
                    payment.save()
                    
                    TransactionLog.objects.create(
                        payment=payment,
                        event_type='async_payment_failed',
                        details={'session_id': session.get('id')}
                    )
                    print(f"⚠️ Async payment failed for payment: {payment_id}")
            except Payment.DoesNotExist:
                pass
            except Exception as e:
                print(f"❌ Error processing checkout.session.expired: {e}")
        
        # Still support old payment_intent events for backward compatibility
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            try:
                payment = Payment.objects.get(
                    stripe_payment_intent_id=payment_intent['id']
                )
                payment.status = 'succeeded'
                payment.save()
                
                TransactionLog.objects.create(
                    payment=payment,
                    event_type='webhook_succeeded',
                    details=event['data']
                )
                print(f"✅ Legacy payment_intent succeeded: {payment_intent['id']}")
            except Payment.DoesNotExist:
                print(f"⚠️ Payment not found for intent: {payment_intent['id']}")
            except Exception as e:
                print(f"❌ Error processing payment_intent.succeeded: {e}")
                
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            
            try:
                payment = Payment.objects.get(
                    stripe_payment_intent_id=payment_intent['id']
                )
                payment.status = 'failed'
                payment.save()
                
                TransactionLog.objects.create(
                    payment=payment,
                    event_type='webhook_failed',
                    details=event['data']
                )
                print(f"⚠️ Legacy payment_intent failed: {payment_intent['id']}")
            except Payment.DoesNotExist:
                print(f"⚠️ Payment not found for intent: {payment_intent['id']}")
            except Exception as e:
                print(f"❌ Error processing payment_intent.payment_failed: {e}")
        
        # Return 200 for all events (even if not handled)
        return HttpResponse(status=200)


class PaymentHistoryView(APIView):
    """Get user's payment history"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DownloadReceiptView(APIView):
    """Get receipt details for a specific payment"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)


class VerifyPaymentSessionView(APIView):
    """
    Manually verify a Stripe Checkout Session status.
    This serves as a backup to webhooks to ensure users get immediate access
    if the webhook is delayed or fails.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Retrieve session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            
            # 2. Check if paid
            if session.payment_status != 'paid':
                return Response({
                    'status': 'unpaid',
                    'message': 'Payment has not been completed yet.'
                }, status=status.HTTP_200_OK)

            # 3. Get metadata to find user/payment
            payment_id = session.get('metadata', {}).get('payment_id')
            user_id = session.get('metadata', {}).get('user_id')

            # 4. Verify user owns this session
            if str(request.user.id) != user_id:
                return Response({'error': 'Unauthorized session verification'}, status=status.HTTP_403_FORBIDDEN)

            # 5. Update Payment Record
            if payment_id:
                try:
                    payment = Payment.objects.get(id=payment_id)
                    
                    # Update status if not already succeeded
                    if payment.status != 'succeeded':
                        payment.status = 'succeeded'
                        payment.stripe_checkout_session_id = session.id
                        payment.generate_receipt_number()
                        payment.save()
                        
                        # Log manual verification
                        TransactionLog.objects.create(
                            payment=payment,
                            event_type='manual_verification_success',
                            details={'session_id': session.id}
                        )
                except Payment.DoesNotExist:
                    pass # Should not happen if metadata is correct

            # 6. Update User Profile (The Critical Part)
            user = request.user
            profile_updated = False
            
            if user.user_type == 'general':
                profile = user.general_profile
                if not profile.has_paid:
                    profile.has_paid = True
                    profile.save()
                    profile_updated = True
            elif user.user_type == 'agency_referred':
                profile = user.referred_profile
                if not profile.has_paid:
                    profile.has_paid = True
                    profile.save()
                    profile_updated = True

            return Response({
                'status': 'paid',
                'verified': True,
                'profile_updated': profile_updated,
                'message': 'Payment verified successfully'
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Verification failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

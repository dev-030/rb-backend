"""Serializers for payment processing"""

from rest_framework import serializers
from users.models import Payment


class CheckoutSessionSerializer(serializers.Serializer):
    """Serializer for creating Stripe Checkout Session"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(max_length=255, required=False, default='Registration Fee')


class CheckoutSessionResponseSerializer(serializers.Serializer):
    """Response serializer for checkout session creation"""
    checkout_url = serializers.URLField()
    session_id = serializers.CharField()
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'stripe_checkout_session_id', 'stripe_payment_intent_id',
            'amount', 'currency', 'payment_method', 'status',
            'receipt_url', 'receipt_number', 'description',
            'case_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

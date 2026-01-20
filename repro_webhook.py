import json
import stripe

# This mimics the structure provided by the user
user_provided_data_content = {
    "id": "cs_test_a14KXEAm78f5P5lNvQhgHdSBvalebsF0b3RToJch8XXFLeRelKvMK6C2iP",
    "object": "checkout.session",
    "metadata": {
      "payment_id": "a30a852d-f128-430a-ba1b-4259d30284c6",
      "user_email": "woodr1970@gmail.com",
      "user_id": "5e66c840-9c3d-43c7-8f8b-624190fedb2b",
      "user_type": "agency_referred"
    },
    "payment_intent": "pi_3Sjpm1PKgHjEgM7q1HrbL26H",
    "payment_status": "paid",
}

print("Creating Stripe Object from dictionary...")
# Convert dict to Stripe Object to simulate real webhook payload
session = stripe.util.convert_to_stripe_object(
    user_provided_data_content, 
    api_key=None, 
    account=None
)

print(f"Session Type: {type(session)}")

print("\n--- Testing Access Methods ---")

# 1. Dictionary access
try:
    print(f"session['id']: {session['id']}")
except Exception as e:
    print(f"❌ session['id'] failed: {e}")

# 2. Dot access (Stripe objects usually support this)
try:
    print(f"session.id: {session.id}")
except Exception as e:
    print(f"❌ session.id failed: {e}")

# 3. Metadata dictionary access
try:
    payment_id = session.get('metadata', {}).get('payment_id')
    print(f"session.get('metadata').get('payment_id'): {payment_id}")
except Exception as e:
    print(f"❌ Metadata extraction failed: {e}")

# 4. Check if metadata is a dict or StripeObject
metadata = session.get('metadata')
print(f"Metadata Type: {type(metadata)}")
if metadata:
    print(f"Metadata Content: {metadata}")

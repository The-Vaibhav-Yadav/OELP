import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hmac
import hashlib

from . import crud, schema, security, database, config, models

# Initialize the router
router = APIRouter()

# It's better to create the client inside the endpoint to ensure thread safety
# but the keys are loaded from the config for use.
RAZORPAY_KEY_ID = config.settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = config.settings.RAZORPAY_KEY_SECRET

@router.post("/create_razorpay_order", response_model=dict)
def create_razorpay_order(
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Creates a Razorpay Order for the current user to purchase a subscription.

    Returns:
        dict: A dictionary containing the order details needed for the frontend.
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials are not configured on the server.")

    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        # Amount should be in the smallest currency unit (e.g., paise for INR)
        # For this example, let's assume a subscription price of 499 INR.
        # In a real application, you would fetch this from a 'plans' table or config.
        amount_in_inr = 499
        amount_in_paise = amount_in_inr * 100

        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_user_{current_user.id}_{int(datetime.now().timestamp())}",
            "notes": {
                "user_id": str(current_user.id) # Razorpay notes must be strings
            }
        }

        order = client.order.create(data=order_data)

        # Return the necessary details for the frontend to initialize Razorpay's checkout
        return {
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "key_id": RAZORPAY_KEY_ID,
            "user_email": current_user.email,
            "user_contact": "9999999999" # Placeholder contact
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Razorpay order: {str(e)}")


@router.post("/razorpay_webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None), db: Session = Depends(database.get_db)):
    """
    Webhook endpoint to receive events from Razorpay.
    This is used to update the user's subscription status after a successful payment.
    """
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="X-Razorpay-Signature header missing.")

    payload_body = await request.body()

    # --- Verify Webhook Signature ---
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        client.utility.verify_webhook_signature(payload_body.decode('utf-8'), x_razorpay_signature, config.settings.RAZORPAY_WEBHOOK_SECRET)
    except razorpay.errors.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Razorpay signature: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook verification failed: {e}")

    # --- Process the Event ---
    try:
        event_data = await request.json()
        event_type = event_data.get('event')

        # Handle the payment.captured event
        if event_type == 'payment.captured':
            payment_entity = event_data['payload']['payment']['entity']
            user_id = payment_entity.get('notes', {}).get('user_id')

            if user_id:
                # --- Logic to update subscription ---
                user_id = int(user_id)
                
                # For simplicity, we'll set the expiration to 31 days from now.
                expires_at = datetime.now() + timedelta(days=31)

                crud.create_or_update_subscription(
                    db=db,
                    user_id=user_id,
                    stripe_customer_id=None, # This field is Stripe-specific; can be ignored or reused
                    is_active=True,
                    expires_at=expires_at
                )
                print(f"Successfully updated subscription for user_id: {user_id} via Razorpay.")

    except Exception as e:
        # It's important to log the error but return a 200 to Razorpay
        # to prevent them from repeatedly sending the same webhook.
        print(f"Error processing Razorpay webhook payload: {e}")
        return {"status": "error during processing"}
            
    return {"status": "success"}


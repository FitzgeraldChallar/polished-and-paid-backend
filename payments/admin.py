from django.contrib import admin
from .models import Payment
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin): list_display=['order','provider','amount','currency','status','stripe_checkout_session_id','created_at']; list_filter=['provider','status','currency']; search_fields=['order__order_number','stripe_checkout_session_id','stripe_payment_intent_id']; readonly_fields=['raw_response','created_at','updated_at']

from decimal import Decimal
import stripe
from django.conf import settings
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from orders.models import Order
from .models import Payment
stripe.api_key=settings.STRIPE_SECRET_KEY
class CreateStripeCheckoutView(APIView):
    permission_classes=[AllowAny]
    @transaction.atomic
    def post(self,request):
        order_id=request.data.get('order_id'); order=Order.objects.filter(pk=order_id).prefetch_related('items').first()
        if not order:return Response({'detail':'Order not found.'},status=404)
        if order.user_id and request.user.is_authenticated and order.user_id!=request.user.id:return Response({'detail':'Not allowed.'},status=403)
        if not settings.STRIPE_SECRET_KEY:return Response({'detail':'Stripe is not configured. Add STRIPE_SECRET_KEY to .env.'},status=503)
        payment,_=Payment.objects.get_or_create(order=order,defaults={'amount':order.total,'currency':order.currency,'status':'pending'})
        line_items=[]
        for item in order.items.all():
            line_items.append({'price_data':{'currency':settings.STRIPE_CURRENCY,'product_data':{'name':item.product_name,'metadata':{'sku':item.sku}},'unit_amount':int(Decimal(item.unit_price)*100)},'quantity':item.quantity})
        if order.shipping_fee>0: line_items.append({'price_data':{'currency':settings.STRIPE_CURRENCY,'product_data':{'name':'Shipping'},'unit_amount':int(order.shipping_fee*100)},'quantity':1})
        if order.tax>0: line_items.append({'price_data':{'currency':settings.STRIPE_CURRENCY,'product_data':{'name':'Tax'},'unit_amount':int(order.tax*100)},'quantity':1})
        session=stripe.checkout.Session.create(mode='payment',line_items=line_items,customer_email=order.email,success_url=f'{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&order={order.order_number}',cancel_url=f'{settings.FRONTEND_URL}/checkout/cancelled?order={order.order_number}',metadata={'order_id':str(order.id),'order_number':order.order_number})
        payment.stripe_checkout_session_id=session.id; payment.raw_response={'id':session.id,'payment_status':session.payment_status}; payment.save(update_fields=['stripe_checkout_session_id','raw_response','updated_at'])
        return Response({'checkout_url':session.url,'session_id':session.id,'order':order.order_number})
class StripeWebhookView(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    def post(self,request):
        payload=request.body; sig=request.META.get('HTTP_STRIPE_SIGNATURE','')
        if not settings.STRIPE_WEBHOOK_SECRET:return Response({'detail':'Webhook secret not configured.'},status=503)
        try:event=stripe.Webhook.construct_event(payload,sig,settings.STRIPE_WEBHOOK_SECRET)
        except Exception:return Response({'detail':'Invalid webhook.'},status=400)
        event_type=event['type']; obj=event['data']['object']; session_id=obj.get('id')
        payment=Payment.objects.filter(stripe_checkout_session_id=session_id).select_related('order').first()
        if payment:
            if event_type=='checkout.session.completed':
                payment.status='paid'; payment.stripe_payment_intent_id=obj.get('payment_intent') or ''; payment.raw_response=obj; payment.order.status='paid'; payment.order.save(update_fields=['status','updated_at']);
                with transaction.atomic():
                    for item in payment.order.items.select_related('product').select_for_update():
                        if item.product and item.product.stock_quantity>=item.quantity:
                            item.product.stock_quantity-=item.quantity; item.product.save(update_fields=['stock_quantity','updated_at'])
            elif event_type=='checkout.session.async_payment_failed': payment.status='failed'; payment.order.status='pending'; payment.order.save(update_fields=['status','updated_at'])
            elif event_type=='checkout.session.expired': payment.status='cancelled'
            payment.save(update_fields=['status','stripe_payment_intent_id','raw_response','updated_at'])
        return Response({'received':True})

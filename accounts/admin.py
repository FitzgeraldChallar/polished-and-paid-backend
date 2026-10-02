from django.contrib import admin
from .models import CustomerProfile, Address
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin): list_display=['user','phone','marketing_opt_in','created_at']; search_fields=['user__email','user__first_name','user__last_name']
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin): list_display=['user','label','city','state','country','is_default']; list_filter=['country','is_default']; search_fields=['user__email','line1','city']

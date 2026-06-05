from django.contrib import admin
from .models import Customer, Transaction, LoyaltyProfile, Campaign, PredictionResult


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_id', 'gender', 'location', 'purchase_category', 'created_at']
    search_fields = ['name', 'email', 'customer_id']
    list_filter = ['gender', 'income_level', 'purchase_channel']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'date', 'payment_method', 'discount_used']
    list_filter = ['payment_method', 'discount_used']
    search_fields = ['customer__name']


@admin.register(LoyaltyProfile)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ['customer', 'tier', 'points', 'total_spending', 'is_member']
    list_filter = ['tier', 'is_member']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_tier', 'discount_percentage', 'is_active', 'start_date', 'end_date']
    list_filter = ['is_active', 'target_tier']


@admin.register(PredictionResult)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'churn_probability', 'repurchase_probability', 'will_repurchase', 'predicted_at']

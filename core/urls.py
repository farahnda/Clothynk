from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/revenue-chart/', views.revenue_chart_data, name='revenue_chart_data'),

    # Customer
    path('customer/', views.customer_list, name='customer_list'),
    path('customer/add/', views.customer_add, name='customer_add'),
    path('customer/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customer/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customer/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customer/<int:pk>/predict/', views.predict_single, name='predict_single'),

    # Transaksi
    path('transaction/', views.transaction_list, name='transaction_list'),
    path('transaction/add/', views.transaction_add, name='transaction_add'),

    # Loyalty
    path('loyalty/', views.loyalty_list, name='loyalty_list'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Campaign
    path('campaign/', views.campaign_list, name='campaign_list'),
    path('campaign/add/', views.campaign_add, name='campaign_add'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'), 
    path('campaign/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaign/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
]

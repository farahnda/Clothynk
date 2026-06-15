from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/revenue-chart/', views.revenue_chart_data, name='revenue_chart_data'),

    # Customer
    path('pelanggan/', views.customer_list, name='customer_list'),
    path('pelanggan/tambah/', views.customer_add, name='customer_add'),
    path('pelanggan/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('pelanggan/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('pelanggan/<int:pk>/hapus/', views.customer_delete, name='customer_delete'),
    path('pelanggan/<int:pk>/prediksi/', views.predict_single, name='predict_single'),

    # Transaksi
    path('transaksi/', views.transaction_list, name='transaction_list'),
    path('transaksi/tambah/', views.transaction_add, name='transaction_add'),

    # Loyalty
    path('loyalty/', views.loyalty_list, name='loyalty_list'),

    # Analytics
    path('analitik/', views.analytics, name='analytics'),

    # Campaign
    path('campaign/', views.campaign_list, name='campaign_list'),
    path('campaign/tambah/', views.campaign_add, name='campaign_add'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'), 
    path('campaign/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaign/<int:pk>/hapus/', views.campaign_delete, name='campaign_delete'),
]

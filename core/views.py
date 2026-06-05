from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import Customer, Transaction, LoyaltyProfile, Campaign, PredictionResult
from .forms import CustomerForm, TransactionForm, CampaignForm
from .ml import run_prediction, run_all_predictions


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    total_customers    = Customer.objects.count()
    total_transactions = Transaction.objects.count()
    total_revenue      = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0
    active_campaigns   = Campaign.objects.filter(is_active=True).count()

    tier_stats = {
        'bronze':   LoyaltyProfile.objects.filter(tier='bronze').count(),
        'silver':   LoyaltyProfile.objects.filter(tier='silver').count(),
        'gold':     LoyaltyProfile.objects.filter(tier='gold').count(),
        'platinum': LoyaltyProfile.objects.filter(tier='platinum').count(),
    }

    seven_days = timezone.now() - timedelta(days=365)
    recent_txn = (
        Transaction.objects
        .filter(date__gte=seven_days)
        .values('date__date')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('date__date')
    )
    chart_labels = [str(r['date__date']) for r in recent_txn]
    chart_data   = [float(r['total']) for r in recent_txn]

    high_risk   = PredictionResult.objects.filter(churn_probability__gte=70).count()
    medium_risk = PredictionResult.objects.filter(churn_probability__gte=40, churn_probability__lt=70).count()
    low_risk    = PredictionResult.objects.filter(churn_probability__lt=40).count()

    recent_transactions = Transaction.objects.select_related('customer').order_by('-date')[:5]

    context = {
        'total_customers': total_customers,
        'total_transactions': total_transactions,
        'total_revenue': total_revenue,
        'active_campaigns': active_campaigns,
        'tier_stats': tier_stats,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'core/dashboard.html', context)


# ─── CUSTOMER ────────────────────────────────────────────────────────────────
@login_required
def customer_list(request):
    q    = request.GET.get('q', '')
    tier = request.GET.get('tier', '')
    customers = Customer.objects.all()
    if q:
        customers = customers.filter(name__icontains=q) | customers.filter(email__icontains=q) | customers.filter(customer_id__icontains=q)
    if tier:
        customers = customers.filter(loyalty__tier=tier)
    return render(request, 'core/customer_list.html', {'customers': customers, 'q': q, 'tier': tier})


@login_required
def customer_detail(request, pk):
    customer     = get_object_or_404(Customer, pk=pk)
    transactions = customer.transactions.order_by('-date')[:10]
    loyalty      = customer.get_loyalty()
    prediction   = getattr(customer, 'prediction', None)

    total_spending = customer.transactions.aggregate(total=Sum('amount'))['total'] or 0
    freq           = customer.transactions.count()
    last_txn       = customer.transactions.order_by('-date').first()

    context = {
        'customer': customer,
        'transactions': transactions,
        'loyalty': loyalty,
        'prediction': prediction,
        'total_spending': total_spending,
        'freq': freq,
        'last_txn': last_txn,
    }
    return render(request, 'core/customer_detail.html', context)


@login_required
def customer_add(request):
    form = CustomerForm(request.POST or None)
    if form.is_valid():
        customer = form.save()
        messages.success(request, f'Pelanggan {customer.name} berhasil ditambahkan!')
        return redirect('customer_detail', pk=customer.pk)
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Tambah Pelanggan'})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, 'Data pelanggan berhasil diperbarui!')
        return redirect('customer_detail', pk=customer.pk)
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Edit Pelanggan', 'customer': customer})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f'Pelanggan {name} berhasil dihapus.')
        return redirect('customer_list')
    return render(request, 'core/customer_confirm_delete.html', {'customer': customer})


# ─── TRANSAKSI ───────────────────────────────────────────────────────────────
@login_required
def transaction_list(request):
    transactions = Transaction.objects.select_related('customer').order_by('-date')[:100]
    total = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'core/transaction_list.html', {'transactions': transactions, 'total': total})


@login_required
def transaction_add(request):
    initial = {}
    customer_id = request.GET.get('customer')
    if customer_id:
        initial['customer'] = customer_id
    form = TransactionForm(request.POST or None, initial=initial)
    if form.is_valid():
        txn = form.save()
        messages.success(request, f'Transaksi ${txn.amount:,.2f} berhasil dicatat!')
        return redirect('transaction_list')
    return render(request, 'core/transaction_form.html', {'form': form, 'title': 'Tambah Transaksi'})


# ─── LOYALTY ─────────────────────────────────────────────────────────────────
@login_required
def loyalty_list(request):
    tier      = request.GET.get('tier', '')
    loyalties = LoyaltyProfile.objects.select_related('customer').order_by('-total_spending')
    if tier:
        loyalties = loyalties.filter(tier=tier)

    tier_counts = {
        'bronze':   LoyaltyProfile.objects.filter(tier='bronze').count(),
        'silver':   LoyaltyProfile.objects.filter(tier='silver').count(),
        'gold':     LoyaltyProfile.objects.filter(tier='gold').count(),
        'platinum': LoyaltyProfile.objects.filter(tier='platinum').count(),
    }
    return render(request, 'core/loyalty_list.html', {'loyalties': loyalties, 'tier_counts': tier_counts, 'tier': tier})


# ─── ANALYTICS / PREDIKSI ────────────────────────────────────────────────────
@login_required
def analytics(request):
    if request.method == 'POST':
        run_all_predictions()
        messages.success(request, 'Prediksi berhasil dijalankan untuk semua pelanggan!')

    predictions = PredictionResult.objects.select_related('customer').order_by('-churn_probability')
    high_risk   = predictions.filter(churn_probability__gte=70)
    medium_risk = predictions.filter(churn_probability__gte=40, churn_probability__lt=70)
    low_risk    = predictions.filter(churn_probability__lt=40)

    context = {
        'predictions': predictions,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'total_predicted': predictions.count(),
    }
    return render(request, 'core/analytics.html', context)


@login_required
def predict_single(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    result = run_prediction(customer)
    messages.success(request, f'Prediksi untuk {customer.name}: Churn {result.churn_probability:.1f}%')
    return redirect('customer_detail', pk=pk)


# ─── CAMPAIGN ────────────────────────────────────────────────────────────────
@login_required
def campaign_list(request):
    campaigns = Campaign.objects.all()
    return render(request, 'core/campaign_list.html', {'campaigns': campaigns})


@login_required
def campaign_add(request):
    form = CampaignForm(request.POST or None)
    if form.is_valid():
        campaign = form.save()
        messages.success(request, f'Campaign "{campaign.name}" berhasil dibuat!')
        return redirect('campaign_list')
    return render(request, 'core/campaign_form.html', {'form': form, 'title': 'Buat Campaign Baru'})


@login_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = CampaignForm(request.POST or None, instance=campaign)
    if form.is_valid():
        form.save()
        messages.success(request, 'Campaign berhasil diperbarui!')
        return redirect('campaign_list')
    return render(request, 'core/campaign_form.html', {'form': form, 'title': 'Edit Campaign', 'campaign': campaign})


@login_required
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Campaign berhasil dihapus.')
        return redirect('campaign_list')
    return render(request, 'core/campaign_confirm_delete.html', {'campaign': campaign})

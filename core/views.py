from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json

from .models import Customer, Transaction, LoyaltyProfile, Campaign, PredictionResult
from .forms import CustomerForm, TransactionForm, CampaignForm
from .ml import run_prediction, run_all_predictions


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    # 1. Statistik Dasar
    total_customers    = Customer.objects.count()
    total_transactions = Transaction.objects.count()

    # Hitung Pendapatan Bulan Ini
    today = timezone.now()
    revenue_this_month = Transaction.objects.filter(
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Hitung Pelanggan Baru Bulan Ini
    new_customers_this_month = Customer.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()

    # 2. Distribusi Tier Loyalty
    tier_counts = {
        'bronze':   LoyaltyProfile.objects.filter(tier='bronze').count(),
        'silver':   LoyaltyProfile.objects.filter(tier='silver').count(),
        'gold':     LoyaltyProfile.objects.filter(tier='gold').count(),
        'platinum': LoyaltyProfile.objects.filter(tier='platinum').count(),
    }

    # 3. Data Grafik Pendapatan
    seven_days = today - timedelta(days=365)
    recent_txn = (
        Transaction.objects
        .filter(date__gte=seven_days)
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )
    monthly_labels = [str(r['date__date']) for r in recent_txn]
    monthly_data   = [float(r['total']) for r in recent_txn]
    
    # 4. Top Pelanggan
    top_customers = Customer.objects.annotate(
        total=Sum('transactions__amount')
    ).order_by('-total')[:5]

    # 5. Risiko Churn 
    total_churn_risk = PredictionResult.objects.filter(churn_probability__gte=70).count()
    churn_risks = PredictionResult.objects.filter(
        churn_probability__gte=70
    ).select_related('customer').order_by('-churn_probability')[:5]

    # 6. Transaksi Terbaru
    recent_transactions = Transaction.objects.select_related('customer').order_by('-date')[:5]

# 7. Campaign Teratas & Penghitung Klaim Riil
    active_campaigns = Campaign.objects.filter(
        is_active=True, 
        start_date__lte=today.date(),
        end_date__gte=today.date()
    )

    top_campaign = None
    claimed_count = 0
    claim_percentage = 0

    if active_campaigns.exists():
        top_campaign = max(active_campaigns, key=lambda c: c.get_target_count())
        target_count = top_campaign.get_target_count() or 1

        # Ambil customer ID berdasarkan target tier campaign
        if top_campaign.target_tier == 'all':
            target_customer_ids = Customer.objects.values_list('id', flat=True)
        else:
            target_customer_ids = LoyaltyProfile.objects.filter(tier=top_campaign.target_tier).values_list('customer_id', flat=True)

        # Hitung transaksi yang menggunakan diskon (discount_used=True) dari target customer
        claimed_count = Transaction.objects.filter(
            customer_id__in=target_customer_ids,
            discount_used=True,
            date__date__gte=top_campaign.start_date,
            date__date__lte=top_campaign.end_date
        ).count()

        claim_percentage = min(int((claimed_count / target_count) * 100), 100)

    context = {
        'total_customers': total_customers,
        'new_customers_this_month': new_customers_this_month,
        'total_transactions': total_transactions,
        'revenue_this_month': revenue_this_month,
        'tier_counts': tier_counts,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
        'top_customers': top_customers,
        'total_churn_risk': total_churn_risk,
        'churn_risks': churn_risks,
        'recent_transactions': recent_transactions,
        'top_campaign': top_campaign,
        'claimed_count': claimed_count,
        'claim_percentage': claim_percentage,
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
        messages.success(request, f'Customer {customer.name} added successfully!')
        return redirect('customer_detail', pk=customer.pk)
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Add Customer'})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, 'Customer data updated successfully!')
        return redirect('customer_detail', pk=customer.pk)
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Edit Customer', 'customer': customer})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        name = customer.name
        customer.delete()

        messages.success(
            request,
            f'Customer "{name}" was deleted successfully.'
        )

        return redirect('customer_list')

    return redirect('customer_detail', pk=pk)
# def customer_delete(request, pk):
#     customer = get_object_or_404(Customer, pk=pk)
#     if request.method == 'POST':
#         name = customer.name
#         customer.delete()
#         messages.success(request, f'Customer {name} deleted successfully.')
#         return redirect('customer_list')
#     return render(request, 'core/customer_confirm_delete.html', {'customer': customer})


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
        messages.success(request, f'Transaction ${txn.amount:,.2f} added successfully!')
        return redirect('transaction_list')
    return render(request, 'core/transaction_form.html', {'form': form, 'title': 'Add Transaction'})


# ─── LOYALTY ─────────────────────────────────────────────────────────────────
@login_required
def loyalty_list(request):

    q = request.GET.get('q', '')
    tier = request.GET.get('tier', '')
    sort = request.GET.get('sort', '')

    loyalties = LoyaltyProfile.objects.select_related(
        'customer'
    )

    if q:
        loyalties = loyalties.filter(
            Q(customer__name__icontains=q) |
            Q(customer__email__icontains=q) |
            Q(customer__customer_id__icontains=q)
        )

    if tier:
        loyalties = loyalties.filter(
            tier=tier
        )

    if sort == 'points_desc':
        loyalties = loyalties.order_by('-points')

    elif sort == 'points_asc':
        loyalties = loyalties.order_by('points')

    elif sort == 'spending_desc':
        loyalties = loyalties.order_by('-total_spending')

    elif sort == 'spending_asc':
        loyalties = loyalties.order_by('total_spending')

    else:
        loyalties = loyalties.order_by('-total_spending')

    tier_counts = {
        'bronze': LoyaltyProfile.objects.filter(tier='bronze').count(),
        'silver': LoyaltyProfile.objects.filter(tier='silver').count(),
        'gold': LoyaltyProfile.objects.filter(tier='gold').count(),
        'platinum': LoyaltyProfile.objects.filter(tier='platinum').count(),
    }

    return render(
        request,
        'core/loyalty_list.html',
        {
            'loyalties': loyalties,
            'tier_counts': tier_counts,
            'q': q,
            'tier': tier,
            'sort': sort,
        }
    )

# ─── ANALYTICS / PREDIKSI ────────────────────────────────────────────────────
@login_required
def analytics(request):

    if request.method == 'POST':
        run_all_predictions()
        messages.success(
            request,
            'Prediction successfully run for all customers!'
        )

    q = request.GET.get('q', '')
    risk = request.GET.get('risk', '')
    sort = request.GET.get('sort', '')

    predictions = PredictionResult.objects.select_related(
        'customer'
    )

    # Search
    if q:
        predictions = predictions.filter(
            Q(customer__name__icontains=q) |
            Q(customer__email__icontains=q) |
            Q(customer__customer_id__icontains=q)
        )

    # Risk Filter
    if risk == 'high':
        predictions = predictions.filter(
            churn_probability__gte=70
        )

    elif risk == 'medium':
        predictions = predictions.filter(
            churn_probability__gte=40,
            churn_probability__lt=70
        )

    elif risk == 'low':
        predictions = predictions.filter(
            churn_probability__lt=40
        )

    # Sorting
    if sort == 'churn_desc':
        predictions = predictions.order_by(
            '-churn_probability'
        )

    elif sort == 'churn_asc':
        predictions = predictions.order_by(
            'churn_probability'
        )

    else:
        predictions = predictions.order_by(
            '-predicted_at'
        )

    high_risk = PredictionResult.objects.filter(
        churn_probability__gte=70
    )

    medium_risk = PredictionResult.objects.filter(
        churn_probability__gte=40,
        churn_probability__lt=70
    )

    low_risk = PredictionResult.objects.filter(
        churn_probability__lt=40
    )

    context = {
        'predictions': predictions,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'total_predicted': PredictionResult.objects.count(),

        'q': q,
        'risk': risk,
        'sort': sort,
    }

    return render(
        request,
        'core/analytics.html',
        context
    )

@login_required
def predict_single(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    result = run_prediction(customer)
    messages.success(request, f'Prediction completed for {customer.name}: Churn {result.churn_probability:.1f}% churn risk.')
    return redirect('customer_detail', pk=pk)


# ─── CAMPAIGN ────────────────────────────────────────────────────────────────
@login_required
def campaign_list(request):
    campaigns = Campaign.objects.all().order_by('-id')
    today = timezone.now().date()
    
    # Menghitung klaim untuk setiap campaign
    for campaign in campaigns:
        # Sama dengan logika di dashboard tadi
        if campaign.target_tier == 'all':
            target_customer_ids = Customer.objects.values_list('id', flat=True)
        else:
            target_customer_ids = LoyaltyProfile.objects.filter(
                tier=campaign.target_tier
            ).values_list('customer_id', flat=True)
            
        campaign.claimed_count = Transaction.objects.filter(
            customer_id__in=target_customer_ids,
            discount_used=True,
            date__date__gte=campaign.start_date,
            date__date__lte=campaign.end_date
        ).count()
        
        target_count = campaign.get_target_count() or 1
        campaign.claim_percentage = min(int((campaign.claimed_count / target_count) * 100), 100)

    active_count = campaigns.filter(is_active=True, start_date__lte=today, end_date__gte=today).count()

    return render(request, 'core/campaign_list.html', {
        'campaigns': campaigns, 
        'active_count': active_count
    })

@login_required
def campaign_add(request):
    form = CampaignForm(request.POST or None)
    if form.is_valid():
        campaign = form.save()
        messages.success(request, f'Campaign "{campaign.name}" created successfully!')
        return redirect('campaign_list')
    return render(request, 'core/campaign_form.html', {'form': form, 'title': 'Create New Campaign'})

@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    # 1. Target Audience
    if campaign.target_tier == 'all':
        targeted_customers = Customer.objects.all()
    else:
        targeted_customers = Customer.objects.filter(loyalty__tier=campaign.target_tier)
    
    # 2. Hitung Klaim (Logika sama seperti di dashboard)
    target_customer_ids = targeted_customers.values_list('id', flat=True)
    claimed_count = Transaction.objects.filter(
        customer_id__in=target_customer_ids,
        discount_used=True,
        date__date__gte=campaign.start_date,
        date__date__lte=campaign.end_date
    ).count()
    
    target_count = targeted_customers.count() or 1
    claim_percentage = min(int((claimed_count / target_count) * 100), 100)
        
    context = {
        'campaign': campaign,
        'targeted_customers': targeted_customers,
        'target_count': target_count,
        'claimed_count': claimed_count,
        'claim_percentage': claim_percentage,
    }
    return render(request, 'core/campaign_detail.html', context)
@login_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = CampaignForm(request.POST or None, instance=campaign)
    if form.is_valid():
        form.save()
        messages.success(request, 'Campaign updated successfully!')
        return redirect('campaign_list')
    return render(request, 'core/campaign_form.html', {'form': form, 'title': 'Edit Campaign', 'campaign': campaign})


@login_required
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Campaign deleted successfully.')
        return redirect('campaign_list')
    return render(request, 'core/campaign_confirm_delete.html', {'campaign': campaign})

@login_required
def revenue_chart_data(request):
    period = request.GET.get('period', '6m')
    today = timezone.now()

    if period == '1m':
        start_date = today - timedelta(days=30)
        query = Transaction.objects.filter(date__gte=start_date)

    elif period == '3m':
        start_date = today - timedelta(days=90)
        query = Transaction.objects.filter(date__gte=start_date)

    elif period == '6m':
        start_date = today - timedelta(days=180)
        query = Transaction.objects.filter(date__gte=start_date)

    elif period == '1y':
        start_date = today - timedelta(days=365)
        query = Transaction.objects.filter(date__gte=start_date)

    else:  # all
        query = Transaction.objects.all()

    recent_txn = (
        query
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )

    labels = [str(r['date__date']) for r in recent_txn]
    data = [float(r['total']) for r in recent_txn]

    return JsonResponse({
        'labels': labels,
        'data': data
    })

# @login_required
# def revenue_chart_data(request):
#     period = request.GET.get('period', '6m') # Default 6 bulan
#     today = timezone.now()

#     # Logika filter waktu
#     if period == '1m':
#         start_date = today - timedelta(days=30)
#         query = Transaction.objects.filter(date__gte=start_date)
#     elif period == '3m':
#         start_date = today - timedelta(days=90)
#         query = Transaction.objects.filter(date__gte=start_date)
#     if period == '6m':
#         start_date = today - timedelta(days=180)
#         query = Transaction.objects.filter(date__gte=start_date)
#     elif period == '1y':
#         start_date = today - timedelta(days=365)
#         query = Transaction.objects.filter(date__gte=start_date)
#     else: # 'all' / Semua Waktu
#         query = Transaction.objects.all()

#     # Kelompokkan data berdasarkan tanggal
#     recent_txn = (
#         query
#         .values('date__date')
#         .annotate(total=Sum('amount'))
#         .order_by('date__date')
#     )

#     labels = [str(r['date__date']) for r in recent_txn]
#     data = [float(r['total']) for r in recent_txn]

#     return JsonResponse({
#         'labels': labels,
#         'data': data
#     })
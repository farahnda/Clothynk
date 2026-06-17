from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.http import HttpResponse
import json
import csv
from natsort import natsorted
from django.utils.dateparse import parse_datetime
from decimal import Decimal
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
    q = request.GET.get('q', '')
    tier = request.GET.get('tier', '')
    sort = request.GET.get('sort', 'name')

    customers = Customer.objects.select_related(
        'loyalty'
    )

    # Search
    if q:
        customers = customers.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(customer_id__icontains=q)
        )

    # Filter tier
    if tier:
        customers = customers.filter(
            loyalty__tier=tier
        )

    # Allowed sorting
    allowed_sort = [
        'name', '-name',
        'customer_id', '-customer_id',
        'gender', '-gender',
        'location', '-location',
        'purchase_category', '-purchase_category',
        'purchase_channel', '-purchase_channel',
        'created_at', '-created_at',
        'updated_at', '-updated_at',
        'loyalty__tier', '-loyalty__tier',
    ]

    # Pisahkan logika sorting
    if sort in ['name', '-name', 'customer_id', '-customer_id']:
        # Evaluasi queryset menjadi list untuk menggunakan natsort
        customers = list(customers)
        
        if sort == 'name':
            customers = natsorted(customers, key=lambda c: c.name)
        elif sort == '-name':
            customers = natsorted(customers, key=lambda c: c.name, reverse=True)
        elif sort == 'customer_id':
            customers = natsorted(customers, key=lambda c: c.customer_id)
        elif sort == '-customer_id':
            customers = natsorted(customers, key=lambda c: c.customer_id, reverse=True)
    elif sort in allowed_sort:
        customers = customers.order_by(sort)
    else:
        # Default sorting
        customers = list(customers)
        customers = natsorted(customers, key=lambda c: c.name)

    return render(
        request,
        'core/customer_list.html',
        {
            'customers': customers,
            'q': q,
            'tier': tier,
            'sort': sort,
        }
    )

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

def import_customer_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Mohon unggah file dengan format .csv yang valid.')
            return redirect('customer_list')

        try:
            # Decode file dan bersihkan karakter BOM tersembunyi
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
            
            # Deteksi pemisah otomatis
            delimiter = ';' if decoded_file and ';' in decoded_file[0] else ','
            reader = csv.DictReader(decoded_file, delimiter=delimiter)
            
            success_count = 0
            error_count = 0
            
            for raw_row in reader:
                # Bersihkan spasi pada nama kolom (header) dan isi data
                row = {str(k).strip(): str(v).strip() for k, v in raw_row.items() if k is not None}
                
                customer_id = row.get('customer_id')
                if not customer_id:
                    error_count += 1
                    continue

                try:
                    # Proses simpan atau update sesuai dengan field model asli
                    Customer.objects.update_or_create(
                        customer_id=customer_id, 
                        defaults={
                            'name': row.get('name', ''),
                            'age': int(row.get('age', 0)) if row.get('age') and row.get('age').isdigit() else 0,
                            'gender': row.get('gender', ''),
                            'income_level': row.get('income_level', ''),
                            'marital_status': row.get('marital_status', ''),
                            'education_level': row.get('education_level', ''),
                            'occupation': row.get('occupation', ''),
                            'location': row.get('location', ''),
                            'email': row.get('email', ''),
                            'phone': row.get('phone', ''),  # Kolom phone tetap dipertahankan
                            'purchase_channel': row.get('purchase_channel', ''),
                            'social_media_influence': row.get('social_media_influence', ''),
                            'discount_sensitivity': row.get('discount_sensitivity', ''),
                            'device_used': row.get('device_used', ''),  # Kolom device_used
                            'payment_method': row.get('payment_method', ''),
                            'shipping_preference': row.get('shipping_preference', ''),
                            'purchase_intent': row.get('purchase_intent', ''),
                        }
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"GAGAL SIMPAN ID {customer_id}: {e}")

            messages.success(request, f'Import Selesai! Berhasil: {success_count} data. Gagal/Dilewati: {error_count} data.')
        
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat memproses CSV: {e}')

    return redirect('customer_list')


def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Template_Import_Customer.csv"'
    
    # Menghindari masalah encoding karakter saat dibuka di Excel
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    
    # Menuliskan susunan header yang tepat berdasarkan field model Anda
    writer.writerow([
        'customer_id', 'name', 'age', 'gender', 'income_level', 
        'marital_status', 'education_level', 'occupation', 'location', 
        'email', 'phone', 'purchase_channel', 'social_media_influence', 
        'discount_sensitivity', 'device_used', 'payment_method', 
        'shipping_preference', 'purchase_intent'
    ])
    
    # Menuliskan satu baris contoh data yang valid
    writer.writerow([
        '01-001-CUST', 'John Doe', '25', 'Male', 'Middle', 
        'Single', "Bachelor's", 'Middle', 'Jakarta', 
        'john@example.com', '081234567890', 'Online', 'Medium', 
        'Somewhat Sensitive', 'Mobile', 'Credit Card', 
        'Standard', 'Need-based'
    ])
    
    return response

@login_required
def transaction_list(request):
    # Tangkap parameter sort dari URL, default ke '-date' (terbaru)
    sort = request.GET.get('sort', '-date')
    payment_method_query = request.GET.get('payment_method', '')
    search_query = request.GET.get('q', '')
    
    # Hitung total revenue keseluruhan (lakukan sebelum queryset diubah menjadi list)
    total = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    transactions = Transaction.objects.all()
    
    # Ambil parameter dari URL
    payment_method_query = request.GET.get('payment_method')
    sort_query = request.GET.get('sort')
    search_query = request.GET.get('q')

    # Logika Filter
    if payment_method_query:
        transactions = transactions.filter(payment_method=payment_method_query)
        
    if search_query:
        # Contoh jika ingin search by customer name
        transactions = transactions.filter(customer__name__icontains=search_query)

    # Logika Sorting
    if sort_query:
        transactions = transactions.order_by(sort_query)

    context = {
        'transactions': transactions,
        'payment_method': payment_method_query, # Kirim balik ke template agar state <select> tersimpan
        'sort': sort_query,
        'q': search_query,
    }
    
    # Daftar field yang diizinkan untuk ORM sorting (selain customer name)
    allowed_sort = [
        'date', '-date',
        'amount', '-amount',
        'payment_method', '-payment_method',
        'frequency', '-frequency',
        'satisfaction', '-satisfaction',
        'discount_used', '-discount_used',
        'purchase_category', '-purchase_category',
    ]
    
    # Pisahkan logika sorting
    if sort in ['customer__name', '-customer__name']:
        # Evaluasi queryset menjadi list untuk menggunakan natsort pada foreign key
        transactions = list(transactions)
        
        if sort == 'customer__name':
            transactions = natsorted(transactions, key=lambda t: t.customer.name)
        elif sort == '-customer__name':
            transactions = natsorted(transactions, key=lambda t: t.customer.name, reverse=True)
            
    elif sort in allowed_sort:
        # Gunakan ORM bawaan untuk field angka/tanggal biasa
        transactions = transactions.order_by(sort)
        
    else:
        # Default sorting jika tidak valid
        transactions = transactions.order_by('-date')
        sort = '-date' # Reset variabel
        
    # Batasi ke 100 transaksi setelah di-sort
    # transactions = transactions[:100]
    
    context = {
        'transactions': transactions, 
        'total': total,
        'sort': sort
    }
    return render(request, 'core/transaction_list.html', context)

@login_required
def transaction_add(request):
    initial = {}
    customer_id = request.GET.get('customer')
    if customer_id:
        initial['customer'] = customer_id
    form = TransactionForm(request.POST or None, initial=initial)

    if form.is_valid():
        # 1. Ambil instance dari form, tapi jangan save ke database dulu (commit=False)
        txn_data = form.save(commit=False)
        
        # 2. Tentukan kriteria transaksi yang dianggap "sama"
        # Contoh di bawah ini menganggap transaksi sama jika customer DAN payment_method sama
        existing_txn = Transaction.objects.filter(
            customer=txn_data.customer
        ).first()

        if existing_txn:
            # 3a. Jika data sudah ada, tambahkan frequency-nya
            existing_txn.frequency += 1
            
            # (Opsional) Tambahkan amount jika kamu ingin mengakumulasikan total belanja
            existing_txn.amount += txn_data.amount 
            
            # Update data terbaru dari form (misal satisfaction atau discount yang baru)
            existing_txn.satisfaction = txn_data.satisfaction
            existing_txn.discount_used = txn_data.discount_used
            
            existing_txn.save()
            messages.success(request, f"Transaction updated! Frequency for {existing_txn.customer.name} increased to {existing_txn.frequency}x.")
        else:
            # 3b. Jika data belum ada, set frequency awal ke 1 dan save sebagai baris baru
            txn_data.frequency = 1
            txn_data.save()
            messages.success(request, f"New transaction ${txn_data.amount:,.2f} added successfully!")

        return redirect('transaction_list')
        
    return render(request, 'core/transaction_form.html', {'form': form, 'title': 'Add Transaction'})
    # if form.is_valid():
    #     txn = form.save()
    #     messages.success(request, f'Transaction ${txn.amount:,.2f} added successfully!')
    #     return redirect('transaction_list')
    # return render(request, 'core/transaction_form.html', {'form': form, 'title': 'Add Transaction'})

def import_transaction_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Mohon unggah file dengan format .csv yang valid.')
            return redirect('transaction_list')

        try:
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
            delimiter = ';' if decoded_file and ';' in decoded_file[0] else ','
            reader = csv.DictReader(decoded_file, delimiter=delimiter)
            
            success_count = 0
            error_count = 0
            
            for raw_row in reader:
                row = {str(k).strip(): str(v).strip() for k, v in raw_row.items() if k is not None}
                
                # 1. Cari Customer berdasarkan ID di CSV
                customer_id_csv = row.get('customer_id')
                if not customer_id_csv:
                    error_count += 1
                    continue
                
                customer_obj = Customer.objects.filter(customer_id=customer_id_csv).first()
                
                # Jika customer tidak ditemukan di database, lewati baris ini
                if not customer_obj:
                    print(f"Customer ID {customer_id_csv} tidak ditemukan.")
                    error_count += 1
                    continue

                try:
                    # 2. Parsing Data Khusus (Desimal, Boolean, Tanggal)
                    amount_val = Decimal(row.get('amount', '0'))
                    freq_val = int(row.get('frequency', 1))
                    sat_val = int(row.get('satisfaction', 5))
                    
                    # Konversi string 'true', 'yes', '1' menjadi Boolean True
                    discount_str = row.get('discount_used', '').lower()
                    is_discount = discount_str in ['true', 'yes', '1', 'y']
                    
                    # 3. Buat Transaksi Baru
                    new_transaction = Transaction(
                        customer=customer_obj,
                        amount=amount_val,
                        payment_method=row.get('payment_method', ''),
                        discount_used=is_discount,
                        frequency=freq_val,
                        satisfaction=sat_val,
                        notes=row.get('notes', ''),
                        purchase_category=row.get('purchase_category', '')
                    )
                    
                    # Cek jika ada tanggal khusus di CSV (format YYYY-MM-DD HH:MM:SS)
                    date_str = row.get('date')
                    if date_str:
                        parsed_date = parse_datetime(date_str)
                        if parsed_date:
                            new_transaction.date = parsed_date
                            
                    new_transaction.save()
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"GAGAL SIMPAN TRANSAKSI UNTUK {customer_id_csv}: {e}")

            messages.success(request, f'Import Selesai! Berhasil: {success_count} transaksi. Dilewati/Gagal: {error_count} baris.')
        
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat memproses CSV: {e}')

    return redirect('transaction_list')


def download_transaction_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Template_Import_Transaction.csv"'
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'customer_id', 'amount', 'date', 'payment_method', 
        'discount_used', 'frequency', 'satisfaction', 
        'purchase_category', 'notes'
    ])
    
    # Contoh Data
    writer.writerow([
        '01-001-CUST', '150000.00', '2026-06-17 10:00:00', 'Credit Card', 
        'Yes', '1', '5', 
        'Casual Wear', 'Pembelian pertama diskon member'
    ])
    
    return response

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

    # Dictionary ini menerjemahkan value dari <select> dropdown ke format ORM Django
    dropdown_mapping = {
        'points_desc': '-points',
        'points_asc': 'points',
        'spending_desc': '-total_spending',
        'spending_asc': 'total_spending',
    }

    allowed_header_sort = [
        'customer__name', '-customer__name',
        'tier', '-tier',
        'points', '-points',
        'total_spending', '-total_spending',
        'is_member', '-is_member'
    ]

    # Eksekusi Sorting
    if sort in dropdown_mapping:
        # Jika nilai sort berasal dari dropdown
        loyalties = loyalties.order_by(dropdown_mapping[sort])
    elif sort in allowed_header_sort:
        # Jika nilai sort berasal dari header tabel
        loyalties = loyalties.order_by(sort)
    else:
        # Fallback (Default sorting jika tidak ada parameter atau parameternya ngaco)
        loyalties = loyalties.order_by('-total_spending')
        sort = 'spending_desc' # Kembalikan nilai ke value dropdown agar state tetap terpilih

    # if sort == 'points_desc':
    #     loyalties = loyalties.order_by('-points')

    # elif sort == 'points_asc':
    #     loyalties = loyalties.order_by('points')

    # elif sort == 'spending_desc':
    #     loyalties = loyalties.order_by('-total_spending')

    # elif sort == 'spending_asc':
    #     loyalties = loyalties.order_by('total_spending')

    # else:
    #     loyalties = loyalties.order_by('-total_spending')

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
    # 1. Handle POST Request
    if request.method == 'POST':
        if 'run_prediction' in request.POST:
            # Assuming run_all_predictions is defined elsewhere
            run_all_predictions()
            messages.success(request, 'Prediction successfully run for all customers!')
            return redirect('analytics')

    # 2. Get URL Parameters
    q = request.GET.get('q', '')
    risk = request.GET.get('risk', '')
    sort = request.GET.get('sort', '')

    predictions = PredictionResult.objects.select_related('customer').all()

    # 3. Search Logic
    if q:
        predictions = predictions.filter(
            Q(customer__name__icontains=q) |
            Q(customer__email__icontains=q) |
            Q(customer__customer_id__icontains=q)
        )

    # 4. Risk Filter Logic
    if risk == 'high':
        predictions = predictions.filter(churn_probability__gte=70)
    elif risk == 'medium':
        predictions = predictions.filter(churn_probability__gte=40, churn_probability__lt=70)
    elif risk == 'low':
        predictions = predictions.filter(churn_probability__lt=40)

    # 5. Sorting Logic
    dropdown_mapping = {
        'churn_desc': '-churn_probability',
        'churn_asc': 'churn_probability',
    }

    allowed_header_sort = [
        'repurchase_probability', '-repurchase_probability',
        'churn_probability', '-churn_probability',
        'predicted_at', '-predicted_at',
    ]

    # Handle Dropdown Menu Sorting
    if sort in dropdown_mapping:
        predictions = predictions.order_by(dropdown_mapping[sort])
        
    # Handle Table Header Sorting (ORM)
    elif sort in allowed_header_sort:
        predictions = predictions.order_by(sort)
        
    # Handle Natural Sorting for Customer Name (Like customer_list)
    elif sort in ['customer__name', '-customer__name']:
        predictions = list(predictions)
        if sort == 'customer__name':
            predictions = natsorted(predictions, key=lambda p: p.customer.name)
        else:
            predictions = natsorted(predictions, key=lambda p: p.customer.name, reverse=True)
            
    # Default Sorting Fallback
    else:
        # If no sort is provided, or an invalid one is given, default to Highest Churn
        predictions = predictions.order_by('-churn_probability')
        sort = 'churn_desc' # Set fallback so the dropdown UI matches the default state

    # 6. Data for Stat Cards (Calculated from base objects so they aren't affected by search/sort lists)
    total_predicted = PredictionResult.objects.count()
    high_risk = PredictionResult.objects.filter(churn_probability__gte=70)
    medium_risk = PredictionResult.objects.filter(churn_probability__gte=40, churn_probability__lt=70)
    low_risk = PredictionResult.objects.filter(churn_probability__lt=40)

    context = {
        'predictions': predictions,
        'total_predicted': total_predicted,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'q': q,
        'risk': risk,
        'sort': sort,
    }

    return render(request, 'core/analytics.html', context)

# def analytics(request):

#     if request.method == 'POST':
#         run_all_predictions()
#         messages.success(
#             request,
#             'Prediction successfully run for all customers!'
#         )

#     q = request.GET.get('q', '')
#     risk = request.GET.get('risk', '')
#     sort = request.GET.get('sort', '')

#     predictions = PredictionResult.objects.select_related(
#         'customer'
#     )

#     # Search
#     if q:
#         predictions = predictions.filter(
#             Q(customer__name__icontains=q) |
#             Q(customer__email__icontains=q) |
#             Q(customer__customer_id__icontains=q)
#         )

#     # Risk Filter
#     if risk == 'high':
#         predictions = predictions.filter(
#             churn_probability__gte=70
#         )

#     elif risk == 'medium':
#         predictions = predictions.filter(
#             churn_probability__gte=40,
#             churn_probability__lt=70
#         )

#     elif risk == 'low':
#         predictions = predictions.filter(
#             churn_probability__lt=40
#         )

#     # Sorting
#     if sort == 'churn_desc':
#         predictions = predictions.order_by(
#             '-churn_probability'
#         )

#     elif sort == 'churn_asc':
#         predictions = predictions.order_by(
#             'churn_probability'
#         )

#     else:
#         predictions = predictions.order_by(
#             '-predicted_at'
#         )

#     high_risk = PredictionResult.objects.filter(
#         churn_probability__gte=70
#     )

#     medium_risk = PredictionResult.objects.filter(
#         churn_probability__gte=40,
#         churn_probability__lt=70
#     )

#     low_risk = PredictionResult.objects.filter(
#         churn_probability__lt=40
#     )

#     context = {
#         'predictions': predictions,
#         'high_risk': high_risk,
#         'medium_risk': medium_risk,
#         'low_risk': low_risk,
#         'total_predicted': PredictionResult.objects.count(),

#         'q': q,
#         'risk': risk,
#         'sort': sort,
#     }

#     return render(
#         request,
#         'core/analytics.html',
#         context
#     )



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
    today = timezone.localdate()
    
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


@login_required
def get_customer_loyalty(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    loyalty = customer.get_loyalty()

    if not loyalty:
        return JsonResponse({'error': 'No loyalty data'}, status=404)

    campaigns = Campaign.objects.filter(
        is_active=True,
        start_date__lte=timezone.localdate(),
        end_date__gte=timezone.localdate()
    )

    # filter campaign sesuai tier
    matched_campaigns = []
    for c in campaigns:
        if c.target_tier == 'all' or c.target_tier == loyalty.tier:
            matched_campaigns.append({
                'name': c.name,
                'discount': float(c.discount_percentage),
                'voucher': c.voucher_code,
            })

    return JsonResponse({
        'tier': loyalty.tier,
        'color': loyalty.get_tier_color(),
        'points': loyalty.points,
        'total_spending': float(loyalty.total_spending),
        'campaigns': matched_campaigns
    })

from django.http import JsonResponse
from django.utils import timezone
from .models import Campaign, LoyaltyProfile

@login_required
def get_available_campaigns(request, customer_id):
    today = timezone.localdate()

    try:
        loyalty = LoyaltyProfile.objects.get(customer_id=customer_id)
        tier = loyalty.tier
    except LoyaltyProfile.DoesNotExist:
        tier = None

    campaigns = Campaign.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    )

    if tier:
        campaigns = campaigns.filter(
            Q(target_tier=tier) | Q(target_tier='all')
        )

    data = []
    for c in campaigns:
        data.append({
            "id": c.id,
            "name": c.name,
            "discount": float(c.discount_percentage),
            "voucher": c.voucher_code,
            "tier": c.target_tier
        })

    return JsonResponse({"campaigns": data})
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Non-binary', 'Non-binary'),
        ('Bigender', 'Bigender'),
        ('Genderfluid', 'Genderfluid'),
        ('Polygender', 'Polygender'),
        ('Agender', 'Agender'),
        ('Genderqueer', 'Genderqueer'),
    ]
    INCOME_CHOICES = [('Low', 'Low'), ('Middle', 'Middle'), ('High', 'High')]
    MARITAL_CHOICES = [('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')]
    EDUCATION_CHOICES = [
        ('High School', 'High School'),
        ("Bachelor's", "Bachelor's"),
        ("Master's", "Master's"),
        ('PhD', 'PhD'),
        ('Other', 'Other'),
    ]
    OCCUPATION_CHOICES = [('Low', 'Low'), ('Middle', 'Middle'), ('High', 'High')]
    CHANNEL_CHOICES = [('Online', 'Online'), ('In-Store', 'In-Store'), ('Mixed', 'Mixed')]
    INFLUENCE_CHOICES = [('None', 'None'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')]
    SENSITIVITY_CHOICES = [('Not Sensitive', 'Not Sensitive'), ('Somewhat Sensitive', 'Somewhat Sensitive'), ('Highly Sensitive', 'Highly Sensitive')]
    INTENT_CHOICES = [('Need-based', 'Need-based'), ('Wants-based', 'Wants-based'), ('Impulsive', 'Impulsive')]
    SHIPPING_CHOICES = [('Standard', 'Standard'), ('Express', 'Express'), ('No Preference', 'No Preference')]

    # Identitas
    customer_id     = models.CharField(max_length=30, unique=True, verbose_name='Customer ID')
    name            = models.CharField(max_length=150, verbose_name='Nama')
    age             = models.IntegerField(verbose_name='Umur')
    gender          = models.CharField(max_length=15, choices=GENDER_CHOICES, verbose_name='Gender')
    income_level    = models.CharField(max_length=10, choices=INCOME_CHOICES, verbose_name='Income Level')
    marital_status  = models.CharField(max_length=15, choices=MARITAL_CHOICES, verbose_name='Marital Status')
    education_level = models.CharField(max_length=20, choices=EDUCATION_CHOICES, verbose_name='Education Level')
    occupation      = models.CharField(max_length=10, choices=OCCUPATION_CHOICES, verbose_name='Occupation Level')
    location        = models.CharField(max_length=100, verbose_name='Lokasi')
    email           = models.EmailField(unique=True, verbose_name='Email')
    phone           = models.CharField(max_length=20, blank=True, verbose_name='No. Telepon')

    # Preferensi Belanja
    purchase_category      = models.CharField(max_length=100, verbose_name='Kategori Pembelian')
    purchase_channel       = models.CharField(max_length=30, choices=CHANNEL_CHOICES, verbose_name='Channel Pembelian')
    social_media_influence = models.CharField(max_length=20, choices=INFLUENCE_CHOICES, verbose_name='Pengaruh Media Sosial')
    discount_sensitivity   = models.CharField(max_length=30, choices=SENSITIVITY_CHOICES, verbose_name='Sensitivitas Diskon')
    device_used            = models.CharField(max_length=30, verbose_name='Perangkat yang Digunakan')
    payment_method         = models.CharField(max_length=30, verbose_name='Metode Pembayaran')
    shipping_preference    = models.CharField(max_length=30, choices=SHIPPING_CHOICES, verbose_name='Preferensi Pengiriman')
    purchase_intent        = models.CharField(max_length=20, choices=INTENT_CHOICES, verbose_name='Niat Pembelian')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.customer_id})"

    def get_loyalty(self):
        try:
            return self.loyalty
        except:
            return None

    class Meta:
        ordering = ['id']
        verbose_name = 'Pelanggan'
        verbose_name_plural = 'Pelanggan'


class Transaction(models.Model):
    PAYMENT_CHOICES = [
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('PayPal', 'PayPal'),
        ('Cash', 'Cash'),
        ('Other', 'Other'),
    ]

    customer         = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    amount           = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Transaksi')
    date             = models.DateTimeField(default=timezone.now, verbose_name='Tanggal Transaksi')
    payment_method   = models.CharField(max_length=30, choices=PAYMENT_CHOICES, verbose_name='Metode Pembayaran')
    discount_used    = models.BooleanField(default=False, verbose_name='Pakai Diskon?')
    frequency        = models.IntegerField(default=1, verbose_name='Frekuensi Pembelian')
    return_rate      = models.IntegerField(default=0, verbose_name='Return Rate')
    satisfaction     = models.IntegerField(default=5, verbose_name='Kepuasan Pelanggan')
    time_to_decision = models.IntegerField(default=1, verbose_name='Waktu Keputusan (hari)')
    notes            = models.TextField(blank=True, verbose_name='Catatan')
    created_at       = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        LoyaltyProfile.update_for_customer(self.customer)

    def __str__(self):
        return f"{self.customer.name} - ${self.amount:,.2f} ({self.date.strftime('%d/%m/%Y')})"

    class Meta:
        ordering = ['-date']
        verbose_name = 'Transaksi'
        verbose_name_plural = 'Transaksi'


class LoyaltyProfile(models.Model):
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    customer       = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='loyalty')
    points         = models.IntegerField(default=0, verbose_name='Total Poin')
    tier           = models.CharField(max_length=10, choices=TIER_CHOICES, default='bronze', verbose_name='Level')
    total_spending = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Total Belanja')
    is_member      = models.BooleanField(default=False, verbose_name='Member Loyalty?')
    updated_at     = models.DateTimeField(auto_now=True)

    TIER_THRESHOLDS = {
        'bronze':   (0,     500),
        'silver':   (500,   2000),
        'gold':     (2000,  5000),
        'platinum': (5000,  float('inf')),
    }
    TIER_COLORS = {
        'bronze': '#cd7f32',
        'silver': '#aaa9ad',
        'gold':   '#ffd700',
        'platinum': '#b5c4de',
    }

    @classmethod
    def update_for_customer(cls, customer):
        total = float(sum(t.amount for t in customer.transactions.all()))
        points = int(total // 10)

        tier = 'bronze'
        if total >= 5000:
            tier = 'platinum'
        elif total >= 2000:
            tier = 'gold'
        elif total >= 500:
            tier = 'silver'

        obj, _ = cls.objects.get_or_create(customer=customer)
        obj.points = points
        obj.tier = tier
        obj.total_spending = total
        obj.save()
        return obj

    def get_tier_color(self):
        return self.TIER_COLORS.get(self.tier, '#999')

    def get_next_tier_info(self):
        thresholds = [('bronze', 0), ('silver', 500), ('gold', 2000), ('platinum', 5000)]
        for i, (t, val) in enumerate(thresholds):
            if t == self.tier and i < len(thresholds) - 1:
                next_tier, next_val = thresholds[i + 1]
                remaining = next_val - float(self.total_spending)
                progress = (float(self.total_spending) - val) / (next_val - val) * 100
                return {'next_tier': next_tier, 'remaining': remaining, 'progress': min(progress, 100)}
        return {'next_tier': None, 'remaining': 0, 'progress': 100}

    def __str__(self):
        return f"{self.customer.name} - {self.tier.capitalize()} ({self.points} poin)"

    class Meta:
        verbose_name = 'Loyalty'
        verbose_name_plural = 'Loyalty'


class Campaign(models.Model):
    TARGET_TIER_CHOICES = [('all', 'Semua')] + LoyaltyProfile.TIER_CHOICES

    name                = models.CharField(max_length=150, verbose_name='Nama Campaign')
    description         = models.TextField(verbose_name='Deskripsi')
    start_date          = models.DateField(verbose_name='Mulai')
    end_date            = models.DateField(verbose_name='Selesai')
    target_tier         = models.CharField(max_length=10, choices=TARGET_TIER_CHOICES, default='all', verbose_name='Target Tier')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Diskon (%)')
    voucher_code        = models.CharField(max_length=50, verbose_name='Kode Voucher')
    is_active           = models.BooleanField(default=True, verbose_name='Aktif?')
    created_at          = models.DateTimeField(auto_now_add=True)


    def is_running(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    @property
    def is_upcoming(self):
        today = timezone.now().date()
        return self.start_date > today

    @property
    def is_completed(self):
        today = timezone.now().date()
        return self.end_date < today
    
    def get_target_count(self):
        if self.target_tier == 'all':
            return Customer.objects.count()
        return LoyaltyProfile.objects.filter(tier=self.target_tier).count()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaign'


class PredictionResult(models.Model):
    customer               = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='prediction')
    churn_probability      = models.FloatField(default=0.0, verbose_name='Probabilitas Churn (%)')
    repurchase_probability = models.FloatField(default=0.0, verbose_name='Probabilitas Beli Lagi (%)')
    will_repurchase        = models.BooleanField(default=True, verbose_name='Prediksi Beli Lagi?')
    predicted_at           = models.DateTimeField(auto_now=True)

    def get_risk_label(self):
        if self.churn_probability >= 70:
            return ('danger', 'Risiko Tinggi')
        elif self.churn_probability >= 40:
            return ('warning', 'Risiko Sedang')
        return ('success', 'Risiko Rendah')

    @property
    def recommendation(self):
        if self.churn_probability >= 70:
            return "Risiko Tinggi! Kirim campaign retensi agresif (Voucher: COMEBACK30) untuk mencegah churn."
        elif self.churn_probability >= 40:
            return "Risiko Sedang. Berikan insentif moderat atau upselling fitur (Voucher: TRYAI15) agar kembali aktif."
        else:
            return "Risiko Rendah (Loyal). Pertahankan hubungan dengan penawaran eksklusif tier (Voucher: VIPONLY10)."

    def __str__(self):
        return f"{self.customer.name} - Churn: {self.churn_probability:.1f}%"

    class Meta:
        verbose_name = 'Prediksi'
        verbose_name_plural = 'Prediksi'
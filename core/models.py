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
    PAYMENT_CHOICES = [
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('PayPal', 'PayPal'),
        ('Cash', 'Cash'),
        ('Other', 'Other'),
    ]
    
    # Identitas
    customer_id     = models.CharField(max_length=30, unique=True, verbose_name='Customer ID')
    name            = models.CharField(max_length=150, verbose_name='Name')
    age             = models.IntegerField(verbose_name='Age')
    gender          = models.CharField(max_length=15, choices=GENDER_CHOICES, verbose_name='Gender')
    income_level    = models.CharField(max_length=10, choices=INCOME_CHOICES, verbose_name='Income Level')
    marital_status  = models.CharField(max_length=15, choices=MARITAL_CHOICES, verbose_name='Marital Status')
    education_level = models.CharField(max_length=20, choices=EDUCATION_CHOICES, verbose_name='Education Level')
    occupation      = models.CharField(max_length=10, choices=OCCUPATION_CHOICES, verbose_name='Occupation Level')
    location        = models.CharField(max_length=100, verbose_name='Location')
    email           = models.EmailField(unique=True, verbose_name='Email')
    phone           = models.CharField(max_length=20, blank=True, verbose_name='Phone Number')

    # Preferensi Belanja
    purchase_channel       = models.CharField(max_length=30, choices=CHANNEL_CHOICES, verbose_name='Purchase Channel')
    social_media_influence = models.CharField(max_length=20, choices=INFLUENCE_CHOICES, verbose_name='Social Media Influence')
    discount_sensitivity   = models.CharField(max_length=30, choices=SENSITIVITY_CHOICES, verbose_name='Discount Sensitivity')
    device_used            = models.CharField(max_length=30, verbose_name='Device Used')
    payment_method         = models.CharField(max_length=30, choices=PAYMENT_CHOICES, verbose_name='Payment Method')
    shipping_preference    = models.CharField(max_length=30, choices=SHIPPING_CHOICES, verbose_name='Shipping Preference')
    purchase_intent        = models.CharField(max_length=20, choices=INTENT_CHOICES, verbose_name='Purchase Intent')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.customer_id})"

    def get_loyalty(self):
        try:
            return self.loyalty
        except:
            return None

    class Meta:
        ordering = ['id']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'


class Transaction(models.Model):
    PAYMENT_CHOICES = [
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('PayPal', 'PayPal'),
        ('Cash', 'Cash'),
        ('Other', 'Other'),
    ]
    PURCHASE_CATEGORY_CHOICES = [
        ('Activewear', 'Activewear'),
        ('Baju Cosplay', 'Baju Cosplay'),
        ('Blouse', 'Blouse'),
        ('Bundled Set', 'Bundled Set'),
        ('Cardigan & Sweater', 'Cardigan & Sweater'),
        ('Casual Wear', 'Casual Wear'),
        ('Compression Wear', 'Compression Wear'),
        ('Dress', 'Dress'),
        ('Formal Wear', 'Formal Wear'),
        ('Graphic Tee', 'Graphic Tee'),
        ('Hoodie', 'Hoodie'),
        ('Jacket', 'Jacket'),
        ('Kids & Baby Wear', 'Kids & Baby Wear'),
        ('Loungewear', 'Loungewear'),
        ('Outdoor & Hiking Wear', 'Outdoor & Hiking Wear'),
        ('Pajamas & Sleepwear', 'Pajamas & Sleepwear'),
        ('Polo Shirt', 'Polo Shirt'),
        ('Resort Wear', 'Resort Wear'),
        ('Scrubs & Medical Wear', 'Scrubs & Medical Wear'),
        ('Skirt', 'Skirt'),
        ('Smart Wearables', 'Smart Wearables'),
        ('Sportswear', 'Sportswear'),
        ('T-Shirt', 'T-Shirt'),
        ('Travel Wear', 'Travel Wear'),
        ('Workwear & Blazer', 'Workwear & Blazer'),
    ]

    customer         = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    amount           = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Transaction')
    date             = models.DateTimeField(default=timezone.now, verbose_name='Transaction Date')
    payment_method   = models.CharField(max_length=30, choices=PAYMENT_CHOICES, verbose_name='Payment Method')
    discount_used    = models.BooleanField(default=False, verbose_name='Use Discount?')
    frequency        = models.IntegerField(default=1, verbose_name='Purchase Frequency')
    satisfaction     = models.IntegerField(default=5, verbose_name='Customer Satisfaction')
    notes            = models.TextField(blank=True, verbose_name='Notes')
    created_at       = models.DateTimeField(auto_now_add=True)
    purchase_category = models.CharField(max_length=50, choices=PURCHASE_CATEGORY_CHOICES, verbose_name='Purchase Category')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        LoyaltyProfile.update_for_customer(self.customer)

    def __str__(self):
        return f"{self.customer.name} - ${self.amount:,.2f} ({self.date.strftime('%d/%m/%Y')})"

    class Meta:
        ordering = ['-date']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'


class LoyaltyProfile(models.Model):
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    customer       = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='loyalty')
    points         = models.IntegerField(default=0, verbose_name='Total Points')
    tier           = models.CharField(max_length=10, choices=TIER_CHOICES, default='bronze', verbose_name='Level')
    total_spending = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Total Spending')
    is_member      = models.BooleanField(default=False, verbose_name='Loyalty Member?')
    updated_at     = models.DateTimeField(auto_now=True)

    TIER_THRESHOLDS = {
        'bronze':   (0,     100),
        'silver':   (100,   500),
        'gold':     (500,   1000),
        'platinum': (1000,  float('inf')),
    }
    
    # Warna sudah di-update menggunakan Hex Code Premium yang baru
    TIER_COLORS = {
        'bronze': '#7A3E26',
        'silver': '#8A929A',
        'gold':   '#C48425',
        'platinum': '#3C4450',
    }

    @classmethod
    def update_for_customer(cls, customer):
        total = float(sum(t.amount for t in customer.transactions.all()))
        points = int(total // 10)

        tier = 'bronze'
        if total >= 1000:
            tier = 'platinum'
        elif total >= 500:
            tier = 'gold'
        elif total >= 100:
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
        thresholds = [('bronze', 0), ('silver', 100), ('gold', 500), ('platinum', 1000)]
        for i, (t, val) in enumerate(thresholds):
            if t == self.tier and i < len(thresholds) - 1:
                next_tier, next_val = thresholds[i + 1]
                remaining = next_val - float(self.total_spending)
                
                # Hitung persentase mentah
                raw_progress = (float(self.total_spending) - val) / (next_val - val) * 100
                
                # Gunakan int() untuk "memotong" desimal alih-alih membulatkannya
                # Mencegah 99.8% menjadi 100% palsu
                progress = int(raw_progress) 
                
                return {'next_tier': next_tier, 'remaining': remaining, 'progress': min(progress, 100)}
        return {'next_tier': None, 'remaining': 0, 'progress': 100}

    def __str__(self):
        return f"{self.customer.name} - {self.tier.capitalize()} ({self.points} poin)"

    class Meta:
        verbose_name = 'Loyalty'
        verbose_name_plural = 'Loyalty'


class Campaign(models.Model):
    TARGET_TIER_CHOICES = [('all', 'All')] + LoyaltyProfile.TIER_CHOICES

    name                = models.CharField(max_length=150, verbose_name='Campaign Name')
    description         = models.TextField(verbose_name='Description')
    start_date          = models.DateField(verbose_name='Start Date')
    end_date            = models.DateField(verbose_name='End Date')
    target_tier         = models.CharField(max_length=10, choices=TARGET_TIER_CHOICES, default='all', verbose_name='Target Tier')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Discount (%)')
    voucher_code        = models.CharField(max_length=50, verbose_name='Voucher Code')
    is_active           = models.BooleanField(default=True, verbose_name='Active?')
    created_at          = models.DateTimeField(auto_now_add=True)

    @property
    def is_running(self):
        if not self.is_active:
            return False
        today = timezone.localdate() # Pastikan pakai localdate() di sini juga!
        return self.start_date <= today <= self.end_date

    @property
    def is_upcoming(self):
        if not self.is_active:
            return False
        today = timezone.localdate() # Pastikan pakai localdate()
        return self.start_date > today

    @property
    def is_completed(self):
        today = timezone.localdate() # Pastikan pakai localdate()
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
    churn_probability      = models.FloatField(default=0.0, verbose_name='Churn Probability (%)')
    repurchase_probability = models.FloatField(default=0.0, verbose_name='Repurchase Probability (%)')
    will_repurchase        = models.BooleanField(default=True, verbose_name='Will Repurchase?')
    predicted_at           = models.DateTimeField(auto_now=True)

    def get_risk_label(self):
        if self.churn_probability >= 70:
            return ('danger', 'High Risk')
        elif self.churn_probability >= 40:
            return ('warning', 'Medium Risk')
        return ('success', 'Low Risk')
    
    @property
    def voucher(self):
        # 1. Cari semua campaign yang sedang aktif hari ini
        today = timezone.localdate()
        active_campaigns = Campaign.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).order_by('-discount_percentage') # Urutkan dari diskon TERBESAR ke TERKECIL

        # Jika tidak ada campaign yang sedang berjalan, tampilkan teks default
        if not active_campaigns.exists():
            return "-"

        p = self.churn_probability

        # 2. Sesuaikan voucher dengan tingkat risiko Churn
        if p >= 70:
            # Risiko TINGGI -> Dapatkan voucher diskon TERBESAR (urutan pertama)
            return active_campaigns.first().voucher_code
            
        elif p >= 40:
            # Risiko MENENGAH -> Dapatkan voucher diskon MENENGAH (di tengah-tengah)
            # Jika cuma ada 1 campaign, akan otomatis ambil yang itu
            mid_index = active_campaigns.count() // 2
            return active_campaigns[mid_index].voucher_code
            
        else:
            # Risiko RENDAH -> Dapatkan voucher diskon TERKECIL (urutan terakhir)
            return active_campaigns.last().voucher_code

    # @property
    # def voucher(self):
    #     p = self.churn_probability

    #     if p >= 80:
    #         return "SAVE30NOW"
    #     elif p >= 60:
    #         return "COMEBACK20"
    #     elif p >= 40:
    #         return "TRYAI15"
    #     elif p >= 20:
    #         return "EARLYBIRD10"
    #     else:
    #         return "VIPONLY10"

    @property
    def recommendation(self):
        p = self.churn_probability

        if p >= 80:
            return "Assign account manager and provide high-value retention offer."

        elif p >= 60:
            return "Proactive retention campaign with personalized outreach and targeted incentive."

        elif p >= 40:
            return "Engagement reinforcement through content, feature education, and mild incentives."

        elif p >= 20:
            return "Maintain engagement with loyalty benefits, updates, and periodic check-ins."

        else:
            return "Focus on upsell, referral, and long-term customer value programs."

    def __str__(self):
        return f"{self.customer.name} - Churn: {self.churn_probability:.1f}%"

    class Meta:
        verbose_name = 'Prediction'
        verbose_name_plural = 'Predictions'
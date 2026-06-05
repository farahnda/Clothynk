from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('customer_id', models.CharField(max_length=30, unique=True, verbose_name='Customer ID')),
                ('name', models.CharField(max_length=150, verbose_name='Nama')),
                ('age', models.IntegerField(verbose_name='Umur')),
                ('gender', models.CharField(max_length=15, verbose_name='Gender')),
                ('income_level', models.CharField(max_length=10, verbose_name='Income Level')),
                ('marital_status', models.CharField(max_length=15, verbose_name='Marital Status')),
                ('education_level', models.CharField(max_length=20, verbose_name='Education Level')),
                ('occupation', models.CharField(max_length=10, verbose_name='Occupation Level')),
                ('location', models.CharField(max_length=100, verbose_name='Lokasi')),
                ('email', models.EmailField(unique=True, verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='No. Telepon')),
                ('purchase_category', models.CharField(max_length=100, verbose_name='Kategori Pembelian')),
                ('purchase_channel', models.CharField(max_length=30, verbose_name='Channel Pembelian')),
                ('social_media_influence', models.CharField(max_length=20, verbose_name='Pengaruh Media Sosial')),
                ('discount_sensitivity', models.CharField(max_length=30, verbose_name='Sensitivitas Diskon')),
                ('device_used', models.CharField(max_length=30, verbose_name='Perangkat yang Digunakan')),
                ('payment_method', models.CharField(max_length=30, verbose_name='Metode Pembayaran')),
                ('shipping_preference', models.CharField(max_length=30, verbose_name='Preferensi Pengiriman')),
                ('purchase_intent', models.CharField(max_length=20, verbose_name='Niat Pembelian')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Pelanggan', 'verbose_name_plural': 'Pelanggan', 'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, verbose_name='Nama Campaign')),
                ('description', models.TextField(verbose_name='Deskripsi')),
                ('start_date', models.DateField(verbose_name='Mulai')),
                ('end_date', models.DateField(verbose_name='Selesai')),
                ('target_tier', models.CharField(default='all', max_length=10, verbose_name='Target Tier')),
                ('discount_percentage', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Diskon (%)')),
                ('voucher_code', models.CharField(max_length=50, verbose_name='Kode Voucher')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Campaign', 'verbose_name_plural': 'Campaign', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='LoyaltyProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty', to='core.customer')),
                ('points', models.IntegerField(default=0, verbose_name='Total Poin')),
                ('tier', models.CharField(default='bronze', max_length=10, verbose_name='Level')),
                ('total_spending', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Total Belanja')),
                ('is_member', models.BooleanField(default=False, verbose_name='Member Loyalty?')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Loyalty', 'verbose_name_plural': 'Loyalty'},
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='core.customer')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Total Transaksi')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Tanggal Transaksi')),
                ('payment_method', models.CharField(max_length=30, verbose_name='Metode Pembayaran')),
                ('discount_used', models.BooleanField(default=False, verbose_name='Pakai Diskon?')),
                ('frequency', models.IntegerField(default=1, verbose_name='Frekuensi Pembelian')),
                ('return_rate', models.IntegerField(default=0, verbose_name='Return Rate')),
                ('satisfaction', models.IntegerField(default=5, verbose_name='Kepuasan Pelanggan')),
                ('time_to_decision', models.IntegerField(default=1, verbose_name='Waktu Keputusan (hari)')),
                ('notes', models.TextField(blank=True, verbose_name='Catatan')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Transaksi', 'verbose_name_plural': 'Transaksi', 'ordering': ['-date']},
        ),
        migrations.CreateModel(
            name='PredictionResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='prediction', to='core.customer')),
                ('churn_probability', models.FloatField(default=0.0, verbose_name='Probabilitas Churn (%)')),
                ('repurchase_probability', models.FloatField(default=0.0, verbose_name='Probabilitas Beli Lagi (%)')),
                ('will_repurchase', models.BooleanField(default=True, verbose_name='Prediksi Beli Lagi?')),
                ('predicted_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Prediksi', 'verbose_name_plural': 'Prediksi'},
        ),
    ]

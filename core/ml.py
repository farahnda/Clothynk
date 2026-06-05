"""
Logistic Regression Engine untuk Clothynk CRM
Memprediksi kemungkinan pelanggan akan churn atau melakukan pembelian ulang.

Fitur yang digunakan:
- frequency        : Jumlah transaksi
- total_spending   : Total belanja kumulatif
- days_inactive    : Hari sejak transaksi terakhir
- avg_transaction  : Rata-rata nilai per transaksi
- discount_usage   : Apakah sering pakai diskon
- tier_score       : Skor numerik dari tier loyalty
- satisfaction_avg : Rata-rata kepuasan
"""

import numpy as np
from django.utils import timezone

TIER_SCORE = {'bronze': 1, 'silver': 2, 'gold': 3, 'platinum': 4}


def extract_features(customer):
    txns = customer.transactions.all()
    freq = txns.count()
    if freq == 0:
        return None

    total_spending  = float(sum(t.amount for t in txns))
    avg_transaction = total_spending / freq
    discount_count  = txns.filter(discount_used=True).count()
    discount_ratio  = discount_count / freq
    satisfaction_avg = float(sum(t.satisfaction for t in txns)) / freq

    last_txn = txns.order_by('-date').first()
    days_inactive = (timezone.now() - last_txn.date).days

    loyalty = customer.get_loyalty()
    tier_score = TIER_SCORE.get(loyalty.tier if loyalty else 'bronze', 1)

    return np.array([
        freq,
        total_spending / 1000,
        days_inactive,
        avg_transaction / 100,
        discount_ratio,
        tier_score,
        satisfaction_avg,
    ])


def run_prediction(customer):
    from .models import PredictionResult

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        result, _ = PredictionResult.objects.get_or_create(customer=customer)
        result.churn_probability = 50.0
        result.repurchase_probability = 50.0
        result.will_repurchase = True
        result.save()
        return result

    features = extract_features(customer)
    if features is None:
        result, _ = PredictionResult.objects.get_or_create(customer=customer)
        result.churn_probability = 50.0
        result.repurchase_probability = 50.0
        result.will_repurchase = True
        result.save()
        return result

    np.random.seed(42)
    n_samples = 300
    X_train, y_train = [], []

    for _ in range(n_samples):
        freq_s         = np.random.randint(1, 40)
        spending_s     = np.random.uniform(0.5, 100.0)
        days_s         = np.random.randint(0, 500)
        avg_s          = np.random.uniform(0.1, 20.0)
        discount_s     = np.random.uniform(0, 1)
        tier_s         = np.random.randint(1, 5)
        sat_s          = np.random.uniform(1, 10)

        churn_score = (
            (days_s > 120) * 3 +
            (freq_s < 3) * 2 +
            (spending_s < 2) * 2 +
            (tier_s == 1) * 1 +
            (sat_s < 4) * 2
        )
        label = 1 if churn_score >= 5 else 0

        X_train.append([freq_s, spending_s, days_s, avg_s, discount_s, tier_s, sat_s])
        y_train.append(label)

    X_train = np.array(X_train)
    y_train = np.array(y_train)

    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    model   = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_scaled, y_train)

    X_pred = scaler.transform(features.reshape(1, -1))
    churn_prob      = float(model.predict_proba(X_pred)[0][1]) * 100
    repurchase_prob = 100.0 - churn_prob
    will_repurchase = churn_prob < 50.0

    result, _ = PredictionResult.objects.get_or_create(customer=customer)
    result.churn_probability      = round(churn_prob, 2)
    result.repurchase_probability = round(repurchase_prob, 2)
    result.will_repurchase        = will_repurchase
    result.save()
    return result


def run_all_predictions():
    from .models import Customer
    results = []
    for customer in Customer.objects.all():
        if customer.transactions.exists():
            r = run_prediction(customer)
            results.append(r)
    return results

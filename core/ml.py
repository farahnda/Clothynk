"""
Logistic Regression Engine untuk Clothynk CRM
Memprediksi kemungkinan pelanggan akan churn atau melakukan pembelian ulang.
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

def train_stable_model():
    """Melatih model dengan data sintetis yang seimbang agar hasil bervariasi"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    
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
    
    return scaler, model

def run_prediction(customer, scaler=None, model=None):
    from .models import PredictionResult

    if not scaler or not model:
        try:
             scaler, model = train_stable_model()
        except ImportError:
            result, _ = PredictionResult.objects.get_or_create(customer=customer)
            result.churn_probability = 50.0
            result.repurchase_probability = 50.0
            result.will_repurchase = True
            result.save()
            return result

    features = extract_features(customer)
    
    if features is None:
        # Jika tidak ada transaksi, berikan probabilitas netral atau sedikit tinggi risiko
        churn_prob = 60.0
        repurchase_prob = 40.0
        will_repurchase = False
    else:
        X_pred = scaler.transform(features.reshape(1, -1))
        raw_churn = float(model.predict_proba(X_pred)[0][1]) * 100
        churn_prob = max(0.0, min(100.0, raw_churn))
        
        if churn_prob >= 99.9:
            churn_prob = 100.0
            repurchase_prob = 0.0
        elif churn_prob <= 0.1:
            churn_prob = 0.0
            repurchase_prob = 100.0
        else:
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
    
    # Train model sekali saja untuk seluruh pelanggan
    try:
        scaler, model = train_stable_model()
    except ImportError:
        scaler, model = None, None

    results = []
    # Loop untuk seluruh pelanggan (agar ke-1001 pelanggan terprediksi)
    for customer in Customer.objects.all():
        r = run_prediction(customer, scaler, model)
        results.append(r)
        
    return results
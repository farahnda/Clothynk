from django import forms
from .models import Customer, Transaction, Campaign


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'customer_id', 'name', 'age', 'gender', 'income_level',
            'marital_status', 'education_level', 'occupation', 'location',
            'email', 'phone', 'purchase_category', 'purchase_channel',
            'social_media_influence', 'discount_sensitivity', 'device_used',
            'payment_method', 'shipping_preference', 'purchase_intent',
        ]
        widgets = {
            'customer_id':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'xx-xxx-xxxx'}),
            'name':                 forms.TextInput(attrs={'class': 'form-control'}),
            'age':                  forms.NumberInput(attrs={'class': 'form-control'}),
            'gender':               forms.Select(attrs={'class': 'form-select'}),
            'income_level':         forms.Select(attrs={'class': 'form-select'}),
            'marital_status':       forms.Select(attrs={'class': 'form-select'}),
            'education_level':      forms.Select(attrs={'class': 'form-select'}),
            'occupation':           forms.Select(attrs={'class': 'form-select'}),
            'location':             forms.TextInput(attrs={'class': 'form-control'}),
            'email':                forms.EmailInput(attrs={'class': 'form-control'}),
            'phone':                forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_category':    forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_channel':     forms.Select(attrs={'class': 'form-select'}),
            'social_media_influence': forms.Select(attrs={'class': 'form-select'}),
            'discount_sensitivity': forms.Select(attrs={'class': 'form-select'}),
            'device_used':          forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method':       forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_preference':  forms.Select(attrs={'class': 'form-select'}),
            'purchase_intent':      forms.Select(attrs={'class': 'form-select'}),
        }


class TransactionForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        label='Tanggal Transaksi'
    )

    class Meta:
        model = Transaction
        fields = ['customer', 'amount', 'date', 'payment_method', 'discount_used', 'frequency', 'return_rate', 'satisfaction', 'time_to_decision', 'notes']
        widgets = {
            'customer':         forms.Select(attrs={'class': 'form-select'}),
            'amount':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method':   forms.Select(attrs={'class': 'form-select'}),
            'discount_used':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frequency':        forms.NumberInput(attrs={'class': 'form-control'}),
            'return_rate':      forms.NumberInput(attrs={'class': 'form-control'}),
            'satisfaction':     forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'time_to_decision': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes':            forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CampaignForm(forms.ModelForm):
    # Tambahkan format='%Y-%m-%d' agar tanggal lama muncul saat diedit
    start_date = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d', 
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    end_date = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d', 
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )

    class Meta:
        model = Campaign
        fields = ['name', 'description', 'start_date', 'end_date', 'target_tier', 'discount_percentage', 'voucher_code', 'is_active']
        widgets = {
            'name':                forms.TextInput(attrs={'class': 'form-control'}),
            'description':         forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'target_tier':         forms.Select(attrs={'class': 'form-select'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'voucher_code':        forms.TextInput(attrs={'class': 'form-control'}),
            'is_active':           forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
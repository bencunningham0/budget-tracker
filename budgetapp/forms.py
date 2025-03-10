from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Budget, Income, Transaction, RecurringTransaction, IncomeTransaction, UserProfile
import pytz

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

# User Settings Forms
class UserSettingsForm(forms.ModelForm):
    """Form for updating basic user information"""
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ProfileSettingsForm(forms.ModelForm):
    """Form for updating user profile settings"""
    timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        required=True,
        help_text="Select your local timezone to ensure dates and times are displayed correctly."
    )

    class Meta:
        model = UserProfile
        fields = ['timezone']

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'frequency', 'rollover', 'rollover_max']
        widgets = {
            'rollover_max': forms.NumberInput(attrs={'step': '0.01'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rollover_max'].required = False

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['source', 'amount', 'frequency', 'is_variable']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_variable'].label = "Variable Income"
        self.fields['is_variable'].help_text = "Check this if your income amount varies from period to period"

class IncomeTransactionForm(forms.ModelForm):
    class Meta:
        model = IncomeTransaction
        fields = ['income', 'amount', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['income'].queryset = Income.objects.filter(user=user)
            
        # Set default description if not provided
        if not self.initial.get('description'):
            self.initial['description'] = 'Income payment'

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['budget', 'amount', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['budget'].queryset = Budget.objects.filter(user=user)

class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ['budget', 'amount', 'description', 'frequency', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['budget'].queryset = Budget.objects.filter(user=user)
        self.fields['end_date'].required = False
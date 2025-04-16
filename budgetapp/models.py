from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta, datetime, date
from decimal import Decimal
import pytz
from threading import Thread

# User Profile model to store additional user settings
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(max_length=50, default='UTC', choices=[(tz, tz) for tz in pytz.common_timezones])
    
    def __str__(self):
        return f"{self.user.username}'s profile"

# Signal handler to create user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

class Budget(models.Model):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets', db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, db_index=True)
    rollover = models.BooleanField(default=False, db_index=True)
    rollover_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Precomputed fields for performance
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_weekly_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Use JSONField if available, else TextField for JSON-serialized data
    historical_periods = models.JSONField(default=list, blank=True)  # If not available, use TextField
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'frequency']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.get_frequency_display()})"

    def get_start_date(self):
        """Calculate the effective start date based on the oldest transaction"""
        oldest_transaction = self.transactions.order_by('date').first()
        if oldest_transaction:
            return self.get_period_start_for_date(oldest_transaction.date.date())
        return self.get_period_start_for_date(self.created_at.date())

    def get_current_balance(self):
        # Use select_related to optimize related table lookups
        transactions = self.transactions.select_related('recurring_transaction').all()
        
        # Calculate the starting budget amount for the current period
        period_start = self.get_current_period_start()
        
        # Convert to timezone-aware datetime for comparison
        period_start_dt = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
        
        # Get transactions from this period
        current_period_transactions = transactions.filter(date__gte=period_start_dt)
        
        # Calculate spent amount in current period
        spent = sum(t.amount for t in current_period_transactions)
        
        # Calculate rollover amount if applicable
        rollover_amount = 0
        if self.rollover:
            # Check if this is the first period
            start_date = self.get_start_date()
            if start_date >= period_start:
                # If the budget was created during the current period,
                # we shouldn't add any rollover as it's the first period
                rollover_amount = 0
            else:
                # Get last period's unused funds
                last_period_end = period_start - timedelta(days=1)
                last_period_start = self.get_period_start_for_date(last_period_end)
                
                # Check if last period is valid (after start date)
                if last_period_start < start_date:
                    last_period_start = start_date
                
                # Convert to timezone-aware datetime for comparison
                last_period_start_dt = timezone.make_aware(datetime.combine(last_period_start, datetime.min.time()))
                
                last_period_transactions = transactions.filter(
                    date__gte=last_period_start_dt,
                    date__lt=period_start_dt
                )
                
                last_period_spent = sum(t.amount for t in last_period_transactions)
                last_period_budget = self.amount
                
                # Calculate rollover amount
                rollover_amount = max(0, last_period_budget - last_period_spent)
                
                # Apply rollover_max limit if set
                if self.rollover_max is not None:
                    rollover_amount = min(rollover_amount, self.rollover_max)
        
        # Return current balance
        return self.amount + rollover_amount - spent
    
    def get_current_period_start(self):
        today = timezone.now().date()
        return self.get_period_start_for_date(today)
    
    def get_period_start_for_date(self, date):
        if self.frequency == 'weekly':
            # Get the Monday of the current week
            return date - timedelta(days=date.weekday())
        elif self.frequency == 'fortnightly':
            # Get Monday of the current or previous week depending on if it's a budget week
            monday = date - timedelta(days=date.weekday())
            # Use start_date calculated from transactions
            reference_date = self.get_start_date()
            reference_monday = reference_date - timedelta(days=reference_date.weekday())
            days_diff = (monday - reference_monday).days
            weeks_diff = days_diff // 7
            if weeks_diff % 2 == 1:  # odd number of weeks difference
                monday = monday - timedelta(days=7)  # go back to previous week
            return monday
        elif self.frequency == 'monthly':
            # Get the 1st of the current month
            return date.replace(day=1)
        else:  # yearly
            # Get the 1st day of the year
            return date.replace(month=1, day=1)
            
    def get_period_end_for_date(self, start_date):
        if self.frequency == 'weekly':
            return start_date + timedelta(days=6)
        elif self.frequency == 'fortnightly':
            return start_date + timedelta(days=13)
        elif self.frequency == 'monthly':
            # Last day of the month
            if start_date.month == 12:
                next_month = date(start_date.year + 1, 1, 1)
            else:
                next_month = date(start_date.year, start_date.month + 1, 1)
            return next_month - timedelta(days=1)
        else:  # yearly
            # Last day of the year
            return date(start_date.year, 12, 31)
            
    
    def get_historical_periods(self, num_periods=6):
        """Return data about previous budget periods"""
        # Prefetch all transactions to avoid N+1 queries
        transactions = self.transactions.all()
        transactions = list(transactions)  # Evaluate queryset once
        
        periods = []
        current_period_start = self.get_current_period_start()
        
        # Start with current period
        periods.append(self._get_period_data(current_period_start, transactions))
        
        # Add previous periods
        for i in range(1, num_periods):
            # Get the end date of the previous period
            prev_period_end = self._get_previous_period_end(periods[-1]['start_date'])
            prev_period_start = self.get_period_start_for_date(prev_period_end)
            
            # Stop if we reach start date
            if prev_period_start < self.get_start_date():
                break
                
            periods.append(self._get_period_data(prev_period_start, transactions))
            
        return periods
        
    def _get_previous_period_end(self, period_start):
        # Get the day before the current period start
        return period_start - timedelta(days=1)
        
    def _get_period_data(self, period_start, transactions=None):
        """Get budget data for a specific period"""
        period_end = self.get_period_end_for_date(period_start)
        
        # Get transactions in this period
        if transactions is None:
            transactions = self.transactions.all()
            transactions = list(transactions)  # Evaluate queryset once
        
        # Convert date objects to timezone-aware datetime for proper comparison
        period_start_dt = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
        period_end_dt = timezone.make_aware(datetime.combine(period_end, datetime.max.time()))
        
        period_transactions = [t for t in transactions 
                             if period_start_dt <= t.date <= period_end_dt]
        
        total_spent = sum(t.amount for t in period_transactions)
        
        # Calculate rollover from previous period if applicable
        rollover_amount = 0
        if self.rollover and period_start > self.get_start_date():
            # Get previous period's end and start dates
            prev_period_end = period_start - timedelta(days=1)
            prev_period_start = self.get_period_start_for_date(prev_period_end)
            
            # Adjust start date if it's before start date
            start_date = self.get_start_date()
            if prev_period_start < start_date:
                prev_period_start = start_date
            
            # Convert date objects to timezone-aware datetime for proper comparison
            prev_period_start_dt = timezone.make_aware(datetime.combine(prev_period_start, datetime.min.time()))
            period_start_dt = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
            
            # Get previous period's transactions
            prev_transactions = [t for t in transactions 
                               if prev_period_start_dt <= t.date < period_start_dt]
            
            prev_spent = sum(t.amount for t in prev_transactions)
            
            # Get rollover from previous period recursively
            if prev_period_start > start_date:
                prev_period_data = self._get_period_data(prev_period_start, transactions)
                rollover_amount = prev_period_data['rollover_amount']
                prev_budget_amount = self.amount + rollover_amount
                rollover_amount = max(0, prev_budget_amount - prev_spent)
            else:
                # For the first period after start date, just calculate based on previous period
                rollover_amount = max(0, self.amount - prev_spent)
            
            # Apply rollover_max limit if set
            if self.rollover_max is not None:
                rollover_amount = min(rollover_amount, self.rollover_max)
        
        # Calculate total budget including rollover
        budget_amount = self.amount + rollover_amount
        
        # Calculate the balance
        balance = budget_amount - total_spent
        
        # Determine if current period
        is_current = (period_start == self.get_current_period_start())
        
        return {
            'start_date': period_start,
            'end_date': period_end,
            'total_spent': total_spent,
            'balance': balance,
            'budget_amount': budget_amount,
            'base_budget': self.amount,
            'rollover_amount': rollover_amount,
            'difference': balance,
            'is_over_budget': balance < 0,
            'is_current': is_current
        }

    def get_current_period_info(self):
        """Get information about the current budget period including balance, amount spent, and budget amount"""
        # Get the current period dates
        period_start = self.get_current_period_start()
        budget = self._get_period_data(period_start)
        return budget

    def get_weekly_amount(self):
        """Get the weekly equivalent of the budget amount"""
        if self.frequency == 'weekly':
            return self.amount
        elif self.frequency == 'fortnightly':
            return self.amount / Decimal('2')
        elif self.frequency == 'monthly':
            return self.amount * Decimal('12') / Decimal('52')
        else:  # yearly
            return self.amount / Decimal('52')

    def get_avg_weekly_spent(self):
        """Calculate the average weekly spend since the first transaction"""
        # Get the first transaction date
        first_transaction = self.transactions.order_by('date').first()
        if not first_transaction:
            return Decimal('0')
            
        # Get all transactions
        all_transactions = self.transactions.all()
        total_spent = sum(t.amount for t in all_transactions)
        
        # Calculate number of weeks
        today = timezone.now().date()
        first_date = first_transaction.date.date()
        days_diff = (today - first_date).days
        weeks = max(Decimal(str(days_diff / 7)), Decimal('1'))  # Use at least 1 week to avoid division by zero
        
        # Return weekly average
        return total_spent / weeks

class Income(models.Model):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('variable', 'Variable'),  # Add variable option for irregular income
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes', db_index=True)
    source = models.CharField(max_length=100, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_variable = models.BooleanField(default=False, db_index=True)
    # Precomputed fields for performance
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_30d = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_90d = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Use JSONField if available, else TextField for JSON-serialized data
    historical_incomes = models.JSONField(default=list, blank=True)  # If not available, use TextField
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'source']),
            models.Index(fields=['user', 'frequency']),
            models.Index(fields=['user', 'is_variable']),
        ]

    def __str__(self):
        return f"{self.source} - {self.amount} ({self.get_frequency_display()})"
    
    def get_weekly_amount(self):
        if self.frequency == 'variable':
            # For variable income, get average weekly income from recent transactions
            recent_period = timezone.now() - timedelta(days=60)  # Last 60 days
            income_transactions = self.income_transactions.filter(date__gte=recent_period)
            
            if income_transactions.exists():
                total_income = sum(t.amount for t in income_transactions)
                weeks = Decimal('8.57')  # Approximately 60/7 weeks
                return total_income / weeks
            # Fall back to the expected amount if no transactions yet
            return self.amount
        elif self.frequency == 'weekly':
            return self.amount
        elif self.frequency == 'fortnightly':
            return self.amount / Decimal('2')
        elif self.frequency == 'monthly':
            return self.amount * Decimal('12') / Decimal('52')
        else:  # yearly
            return self.amount / Decimal('52')

    def get_current_period_actual_income(self):
        """Get actual income for current budget period"""
        if not self.is_variable:
            return self.amount
            
        # Determine period dates based on frequency
        today = timezone.now().date()
        if self.frequency == 'weekly':
            # Start of week (Monday)
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=6)
        elif self.frequency == 'fortnightly':
            # Start of week
            period_start = today - timedelta(days=today.weekday())
            # Determine if this is week 1 or 2 of the fortnight
            # (Simple approach - could be made more sophisticated)
            if (period_start.isocalendar()[1] % 2) == 0:
                period_start -= timedelta(days=7)
            period_end = period_start + timedelta(days=13)
        elif self.frequency == 'monthly':
            # Start of month
            period_start = today.replace(day=1)
            # End of month
            if today.month == 12:
                period_end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:  # yearly or variable
            # Start of year
            period_start = today.replace(month=1, day=1)
            period_end = today.replace(month=12, day=31)
            
        # Get transactions in this period
        income_in_period = self.income_transactions.filter(
            date__gte=timezone.make_aware(datetime.combine(period_start, datetime.min.time())),
            date__lte=timezone.make_aware(datetime.combine(period_end, datetime.min.time()))
        )
        
        # Return the sum of actual income
        if income_in_period.exists():
            return sum(t.amount for t in income_in_period)
        return Decimal('0')

class IncomeTransaction(models.Model):
    """Model for tracking actual income received"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='income_transactions', db_index=True)
    income = models.ForeignKey(Income, on_delete=models.CASCADE, related_name='income_transactions', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['income', 'date']),
        ]

    def __str__(self):
        return f"{self.description} - ${self.amount} ({self.date.date()})"
    
    def save(self, *args, **kwargs):
        # If date is being set for the first time, use start of day
        if self.date:
            # Convert to date and back to datetime to get midnight
            self.date = timezone.make_aware(
                datetime.combine(self.date.date(), datetime.min.time())
            )
        super().save(*args, **kwargs)

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', db_index=True)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transactions', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateTimeField(default=timezone.now, db_index=True)
    recurring_transaction = models.ForeignKey('RecurringTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['budget', 'date']),
        ]

    def __str__(self):
        return f"{self.description} - ${self.amount} ({self.date.date()})"
        
    def save(self, *args, **kwargs):
        # If date is being set for the first time, use start of day
        if self.date:
            # Convert to date and back to datetime to get midnight
            self.date = timezone.make_aware(
                datetime.combine(self.date.date(), datetime.min.time())
            )
        super().save(*args, **kwargs)

class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions', db_index=True)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='recurring_transactions', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, db_index=True)
    start_date = models.DateField(default=date.today, db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    last_generated = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'budget']),
            models.Index(fields=['user', 'active']),
            models.Index(fields=['user', 'start_date']),
        ]

    def __str__(self):
        return f"{self.budget.category}: {self.amount} - {self.description} ({self.get_frequency_display()})"
        
    def generate_transactions(self):
        if not self.active:
            return []
            
        today = date.today()
        if self.end_date and today > self.end_date:
            self.active = False
            self.save()
            return []
            
        created_transactions = []
        next_date = self.start_date if not self.last_generated else self._get_next_date(self.last_generated)
        
        # Generate transactions up to today
        while next_date <= today:
            # Check if transaction already exists for this date
            transaction_date = timezone.make_aware(datetime.combine(next_date, datetime.min.time()))
            existing_transaction = Transaction.objects.filter(
                user=self.user,
                budget=self.budget,
                recurring_transaction=self,
                date=transaction_date
            ).exists()
            
            if not existing_transaction:
                # Create the transaction only if it doesn't exist
                transaction = Transaction(
                    user=self.user,
                    budget=self.budget,
                    amount=self.amount,
                    description=f"{self.description} (Recurring)",
                    date=transaction_date,
                    recurring_transaction=self
                )
                transaction.save()
                created_transactions.append(transaction)
            
            # Update last generated date regardless of whether we created a new transaction
            self.last_generated = next_date
            self.save()
            
            # Calculate next date
            next_date = self._get_next_date(next_date)
            
            # Stop if reached end date
            if self.end_date and next_date > self.end_date:
                break
                
        return created_transactions
        
    def _get_next_date(self, from_date):
        if self.frequency == 'daily':
            return from_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return from_date + timedelta(weeks=1)
        elif self.frequency == 'fortnightly':
            return from_date + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            # Move to the same day next month
            month = from_date.month + 1
            year = from_date.year
            if month > 12:
                month = 1
                year += 1
                
            # Handle cases where the day might not exist in next month
            try:
                return from_date.replace(year=year, month=month)
            except ValueError:
                # If the day doesn't exist in next month, use the last day
                if month == 12:
                    next_month = date(year + 1, 1, 1)
                else:
                    next_month = date(year, month + 1, 1)
                return next_month - timedelta(days=1)
        elif self.frequency == 'yearly':
            return from_date.replace(year=from_date.year + 1)

def update_budget_aggregates(budget):
    transactions = budget.transactions.all()
    total_spent = sum(t.amount for t in transactions)
    avg_weekly_spent = budget.get_avg_weekly_spent()
    # Store up to 52 historical periods
    historical_periods = budget.get_historical_periods(num_periods=52)
    # Use DjangoJSONEncoder to ensure all values are serializable
    historical_periods = json.loads(json.dumps(historical_periods, cls=DjangoJSONEncoder))
    budget.total_spent = total_spent
    budget.avg_weekly_spent = avg_weekly_spent
    budget.historical_periods = historical_periods
    budget.save(update_fields=["total_spent", "avg_weekly_spent", "historical_periods"])

def update_budget_aggregates_async(budget):
    Thread(target=update_budget_aggregates, args=(budget,)).start()

# Signals for Transaction
@receiver(post_save, sender='budgetapp.Transaction')
def transaction_post_save(sender, instance, **kwargs):
    update_budget_aggregates_async(instance.budget)

@receiver(post_delete, sender='budgetapp.Transaction')
def transaction_post_delete(sender, instance, **kwargs):
    update_budget_aggregates_async(instance.budget)

def update_income_aggregates(income):
    """Update precomputed fields for an Income instance."""
    transactions = income.income_transactions.all()
    total_income = sum(t.amount for t in transactions)
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)
    transactions_30d = transactions.filter(date__gte=last_30_days)
    transactions_90d = transactions.filter(date__gte=last_90_days)
    avg_30d = sum(t.amount for t in transactions_30d) / Decimal('30') * Decimal('7') if transactions_30d else Decimal('0')
    avg_90d = sum(t.amount for t in transactions_90d) / Decimal('90') * Decimal('7') if transactions_90d else Decimal('0')
    income.total_income = total_income
    income.avg_30d = avg_30d
    income.avg_90d = avg_90d
    income.save(update_fields=["total_income", "avg_30d", "avg_90d"])

def update_income_aggregates_async(income):
    Thread(target=update_income_aggregates, args=(income,)).start()

# Signals for IncomeTransaction
@receiver(post_save, sender='budgetapp.IncomeTransaction')
def incometransaction_post_save(sender, instance, **kwargs):
    update_income_aggregates_async(instance.income)

@receiver(post_delete, sender='budgetapp.IncomeTransaction')
def incometransaction_post_delete(sender, instance, **kwargs):
    update_income_aggregates_async(instance.income)

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime, date
from decimal import Decimal

class Budget(models.Model):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    rollover = models.BooleanField(default=False)
    rollover_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.category} - {self.amount} ({self.get_frequency_display()})"

    def get_start_date(self):
        """Calculate the effective start date based on the oldest transaction"""
        oldest_transaction = self.transactions.order_by('date').first()
        if oldest_transaction:
            return self.get_period_start_for_date(oldest_transaction.date.date())
        return self.get_period_start_for_date(self.created_at.date())

    def get_current_balance(self):
        # Get all transactions for this budget
        transactions = self.transactions.all()
        
        # Calculate the starting budget amount for the current period
        period_start = self.get_current_period_start()
        
        # Get transactions from this period
        current_period_transactions = transactions.filter(date__gte=period_start)
        
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
                    # If the last period started before the start date,
                    # adjust last_period_start
                    last_period_start = start_date
                
                last_period_transactions = transactions.filter(
                    date__gte=last_period_start,
                    date__lt=period_start
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
        periods = []
        current_period_start = self.get_current_period_start()
        
        # Start with current period
        periods.append(self._get_period_data(current_period_start))
        
        # Add previous periods
        for i in range(1, num_periods):
            # Get the end date of the previous period
            prev_period_end = self._get_previous_period_end(periods[-1]['start_date'])
            prev_period_start = self.get_period_start_for_date(prev_period_end)
            
            # Stop if we reach start date
            if prev_period_start < self.get_start_date():
                break
                
            periods.append(self._get_period_data(prev_period_start))
            
        return periods
        
    def _get_previous_period_end(self, period_start):
        # Get the day before the current period start
        return period_start - timedelta(days=1)
        
    def _get_period_data(self, period_start):
        """Get budget data for a specific period"""
        period_end = self.get_period_end_for_date(period_start)
        
        # Get transactions in this period
        transactions = self.transactions.filter(
            date__gte=period_start,
            date__lte=period_end
        )
        
        total_spent = sum(t.amount for t in transactions)
        
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
            
            # Get previous period's data to calculate rollover
            prev_transactions = self.transactions.filter(
                date__gte=prev_period_start,
                date__lt=period_start
            )
            
            prev_spent = sum(t.amount for t in prev_transactions)
            
            # Get rollover from previous period recursively
            prev_period_data = self._get_period_data(prev_period_start) if prev_period_start > start_date else None
            prev_rollover = prev_period_data['rollover_amount'] if prev_period_data else 0
            prev_budget = self.amount + prev_rollover
            
            # Calculate rollover amount
            remaining = prev_budget - prev_spent
            if remaining > 0:
                rollover_amount = remaining
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    source = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_variable = models.BooleanField(default=False, help_text="Whether this income source varies from period to period")
    
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='income_transactions')
    income = models.ForeignKey(Income, on_delete=models.CASCADE, related_name='income_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateTimeField(default=timezone.now)
    
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateTimeField(default=timezone.now)
    recurring_transaction = models.ForeignKey('RecurringTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='recurring_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)
    last_generated = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    
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
            # Create the transaction
            transaction = Transaction(
                user=self.user,
                budget=self.budget,
                amount=self.amount,
                description=f"{self.description} (Recurring)",
                date=datetime.combine(next_date, datetime.min.time()),
                recurring_transaction=self
            )
            transaction.save()
            created_transactions.append(transaction)
            
            # Update last generated date
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

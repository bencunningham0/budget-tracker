from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from .forms import (
    UserRegistrationForm, BudgetForm, IncomeForm, TransactionForm, 
    RecurringTransactionForm, IncomeTransactionForm
)
from .models import Budget, Income, Transaction, RecurringTransaction, IncomeTransaction

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('dashboard')
        messages.error(request, "Registration failed. Please check the form.")
    else:
        form = UserRegistrationForm()
    return render(request, 'budgetapp/register.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    budgets = Budget.objects.filter(user=user)
    incomes = Income.objects.filter(user=user)
    
    # Process any pending recurring transactions
    process_recurring_transactions(user)
    
    # Calculate total budget spending and remaining
    budget_data = []
    total_budget = 0
    total_spent = 0
    remaining_budget = 0
    
    for budget in budgets:
        period_info = budget.get_current_period_info()
        budget_data.append({
            'budget': budget,
            'balance': period_info['balance'],
            'spent': period_info['total_spent'],
            'weekly_amount': budget.get_weekly_amount(),
            'weekly_spent': budget.get_avg_weekly_spent(),
            'percentage': (period_info['balance'] / period_info['budget_amount']) * Decimal('100') if period_info['budget_amount'] > 0 else Decimal('0')
        })
        total_budget += budget.amount
        remaining_budget += period_info['balance']
        total_spent += period_info['total_spent']
    
    # Calculate total income and weekly averages - updated to handle variable income
    total_weekly_income = sum(income.get_weekly_amount() for income in incomes)
    total_monthly_income = total_weekly_income * Decimal('52') / Decimal('12')
    total_yearly_income = total_weekly_income * Decimal('52')
    
    # Get variable income data
    variable_incomes = [income for income in incomes if income.is_variable]
    variable_income_data = []
    
    for income in variable_incomes:
        recent_period = timezone.now() - timezone.timedelta(days=30)
        income_transactions = IncomeTransaction.objects.filter(
            income=income,
            date__gte=recent_period
        ).order_by('-date')
        
        variable_income_data.append({
            'income': income,
            'recent_transactions': income_transactions[:5],  # Latest 5 transactions
            'actual_period_amount': income.get_current_period_actual_income(),
            'expected_amount': income.amount,
            'difference': income.get_current_period_actual_income() - income.amount
        })
    
    # Calculate weekly budgets and spending
    weekly_budgeted = sum(budget.get_weekly_amount() for budget in budgets)
    weekly_spent = sum(budget.get_avg_weekly_spent() for budget in budgets)
    
    # Calculate remaining income after budgets and spending
    income_remaining_after_budgets = total_weekly_income - weekly_budgeted
    income_remaining_after_spend = total_weekly_income - weekly_spent
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(
        user=user
    ).order_by('-date')[:10]
    
    # Get recent income transactions
    recent_income_transactions = IncomeTransaction.objects.filter(
        user=user
    ).order_by('-date')[:5]
    
    # Get recurring transactions
    recurring_transactions = RecurringTransaction.objects.filter(
        user=user,
        active=True
    ).order_by('start_date')
    
    context = {
        'budget_data': budget_data,
        'total_budget': total_budget,
        'remaining_budget': remaining_budget,
        'weekly_budgeted': weekly_budgeted,
        'weekly_spent': weekly_spent,
        'income_remaining_after_budgets': income_remaining_after_budgets,
        'income_remaining_after_spend': income_remaining_after_spend,
        'total_weekly_income': total_weekly_income,
        'total_monthly_income': total_monthly_income,
        'total_yearly_income': total_yearly_income,
        'recent_transactions': recent_transactions,
        'incomes': incomes,
        'recurring_transactions': recurring_transactions,
        'variable_income_data': variable_income_data,
        'recent_income_transactions': recent_income_transactions,
        'has_variable_income': any(income.is_variable for income in incomes),
    }
    
    return render(request, 'budgetapp/dashboard.html', context)

@login_required
def budget_create(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, "Budget created successfully!")
            return redirect('dashboard')
    else:
        form = BudgetForm()
    
    return render(request, 'budgetapp/budget_form.html', {'form': form, 'action': 'Create'})

@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, "Budget updated successfully!")
            return redirect('dashboard')
    else:
        form = BudgetForm(instance=budget)
    
    return render(request, 'budgetapp/budget_form.html', {'form': form, 'action': 'Edit'})

@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if request.method == 'POST':
        budget.delete()
        messages.success(request, "Budget deleted successfully!")
        return redirect('dashboard')
        
    return render(request, 'budgetapp/budget_confirm_delete.html', {'budget': budget})

@login_required
def budget_detail(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    transactions = Transaction.objects.filter(budget=budget).order_by('-date')
    
    period_info = budget.get_current_period_info()
    
    # Get historical periods data
    historical_periods = budget.get_historical_periods(num_periods=52)
    
    context = {
        'budget': budget,
        'transactions': transactions,
        'balance': period_info['balance'],
        'spent': period_info['total_spent'],
        'percentage': (period_info['balance'] / period_info['budget_amount']) * Decimal('100') if period_info['budget_amount'] > 0 else Decimal('0'),
        'historical_periods': historical_periods,
    }
    
    return render(request, 'budgetapp/budget_detail.html', context)

@login_required
def income_create(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            
            # Auto-set frequency to 'variable' if is_variable is True
            if income.is_variable and income.frequency != 'variable':
                income.frequency = 'variable'
                
            income.save()
            
            messages.success(request, "Income added successfully!")
            
            # Redirect to add income transaction if variable income
            if income.is_variable:
                messages.info(request, "Since this is variable income, you may want to record your first payment.")
                return redirect('income_transaction_create_for_income', income_pk=income.id)
                
            return redirect('dashboard')
    else:
        form = IncomeForm()
    
    return render(request, 'budgetapp/income_form.html', {'form': form, 'action': 'Create'})

@login_required
def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            income = form.save(commit=False)
            
            # Auto-set frequency to 'variable' if is_variable is True
            if income.is_variable and income.frequency != 'variable':
                income.frequency = 'variable'
                
            income.save()
            messages.success(request, "Income updated successfully!")
            return redirect('dashboard')
    else:
        form = IncomeForm(instance=income)
    
    return render(request, 'budgetapp/income_form.html', {'form': form, 'action': 'Edit'})

@login_required
def income_delete(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    
    if request.method == 'POST':
        income.delete()
        messages.success(request, "Income deleted successfully!")
        return redirect('dashboard')
        
    return render(request, 'budgetapp/income_confirm_delete.html', {'income': income})

@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Transaction recorded successfully!")
            return redirect('dashboard')
    else:
        form = TransactionForm(request.user)
    
    return render(request, 'budgetapp/transaction_form.html', {'form': form})

@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Transaction updated successfully!")
            return redirect('budget_detail', pk=transaction.budget.id)
    else:
        form = TransactionForm(request.user, instance=transaction)
    
    return render(request, 'budgetapp/transaction_form.html', {'form': form, 'action': 'Edit'})

@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    budget_id = transaction.budget.id
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, "Transaction deleted successfully!")
        return redirect('budget_detail', pk=budget_id)
        
    return render(request, 'budgetapp/transaction_confirm_delete.html', {'transaction': transaction})

@login_required
def transaction_create_for_budget(request, budget_pk):
    budget = get_object_or_404(Budget, pk=budget_pk, user=request.user)
    
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Transaction recorded successfully!")
            return redirect('budget_detail', pk=budget.id)
    else:
        form = TransactionForm(request.user, initial={'budget': budget})
    
    return render(request, 'budgetapp/transaction_form.html', {'form': form, 'budget': budget})

@login_required
def recurring_transaction_list(request):
    recurring_transactions = RecurringTransaction.objects.filter(
        user=request.user
    ).order_by('budget__category', 'description')
    
    context = {
        'recurring_transactions': recurring_transactions
    }
    
    return render(request, 'budgetapp/recurring_transaction_list.html', context)

@login_required
def recurring_transaction_create(request):
    if request.method == 'POST':
        form = RecurringTransactionForm(request.user, request.POST)
        if form.is_valid():
            recurring_transaction = form.save(commit=False)
            recurring_transaction.user = request.user
            recurring_transaction.save()
            messages.success(request, "Recurring transaction created successfully!")
            return redirect('recurring_transaction_list')
    else:
        form = RecurringTransactionForm(request.user)
    
    return render(request, 'budgetapp/recurring_transaction_form.html', {'form': form, 'action': 'Create'})

@login_required
def recurring_transaction_edit(request, pk):
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = RecurringTransactionForm(request.user, request.POST, instance=recurring_transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Recurring transaction updated successfully!")
            return redirect('recurring_transaction_list')
    else:
        form = RecurringTransactionForm(request.user, instance=recurring_transaction)
    
    return render(request, 'budgetapp/recurring_transaction_form.html', {'form': form, 'action': 'Edit'})

@login_required
def recurring_transaction_delete(request, pk):
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        recurring_transaction.delete()
        messages.success(request, "Recurring transaction deleted successfully!")
        return redirect('recurring_transaction_list')
        
    return render(request, 'budgetapp/recurring_transaction_confirm_delete.html', {'recurring_transaction': recurring_transaction})

@login_required
def recurring_transaction_toggle(request, pk):
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    # Toggle active state
    recurring_transaction.active = not recurring_transaction.active
    recurring_transaction.save()
    
    status = "activated" if recurring_transaction.active else "deactivated"
    messages.success(request, f"Recurring transaction {status} successfully!")
    
    return redirect('recurring_transaction_list')

def process_recurring_transactions(user):
    """Process all recurring transactions for a user"""
    recurring_transactions = RecurringTransaction.objects.filter(
        user=user,
        active=True
    )
    
    for recurring_transaction in recurring_transactions:
        recurring_transaction.generate_transactions()

@login_required
def income_transaction_create(request):
    if request.method == 'POST':
        form = IncomeTransactionForm(request.user, request.POST)
        if form.is_valid():
            income_transaction = form.save(commit=False)
            income_transaction.user = request.user
            income_transaction.save()
            messages.success(request, "Income transaction recorded successfully!")
            return redirect('income_transaction_list')
    else:
        form = IncomeTransactionForm(request.user)
    
    return render(request, 'budgetapp/income_transaction_form.html', {'form': form})

@login_required
def income_transaction_edit(request, pk):
    income_transaction = get_object_or_404(IncomeTransaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = IncomeTransactionForm(request.user, request.POST, instance=income_transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Income transaction updated successfully!")
            return redirect('income_transaction_list')
    else:
        form = IncomeTransactionForm(request.user, instance=income_transaction)
    
    return render(request, 'budgetapp/income_transaction_form.html', {'form': form, 'action': 'Edit'})

@login_required
def income_transaction_delete(request, pk):
    income_transaction = get_object_or_404(IncomeTransaction, pk=pk, user=request.user)
    income_id = income_transaction.income.id
    
    if request.method == 'POST':
        income_transaction.delete()
        messages.success(request, "Income transaction deleted successfully!")
        return redirect('income_transaction_list')
        
    return render(request, 'budgetapp/income_transaction_confirm_delete.html', {'income_transaction': income_transaction})

@login_required
def income_transaction_create_for_income(request, income_pk):
    income = get_object_or_404(Income, pk=income_pk, user=request.user)
    
    if request.method == 'POST':
        form = IncomeTransactionForm(request.user, request.POST)
        if form.is_valid():
            income_transaction = form.save(commit=False)
            income_transaction.user = request.user
            income_transaction.save()
            messages.success(request, "Income transaction recorded successfully!")
            return redirect('income_detail', pk=income.id)
    else:
        form = IncomeTransactionForm(request.user, initial={'income': income})
    
    return render(request, 'budgetapp/income_transaction_form.html', {'form': form, 'income': income})

@login_required
def income_transaction_list(request):
    income_transactions = IncomeTransaction.objects.filter(
        user=request.user
    ).order_by('-date')
    
    # Group by income source
    incomes = Income.objects.filter(user=request.user).order_by('source')
    income_data = []
    
    for income in incomes:
        transactions = income_transactions.filter(income=income)
        if transactions:
            income_data.append({
                'income': income,
                'transactions': transactions,
                'total': sum(t.amount for t in transactions),
                'avg_per_period': income.get_weekly_amount() * 4 if income.frequency != 'variable' else None
            })
    
    context = {
        'income_data': income_data,
        'all_transactions': income_transactions
    }
    
    return render(request, 'budgetapp/income_transaction_list.html', context)

@login_required
def income_detail(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    income_transactions = IncomeTransaction.objects.filter(income=income).order_by('-date')
    
    # Calculate stats for this income source
    current_period_income = income.get_current_period_actual_income()
    expected_income = income.amount
    difference = current_period_income - expected_income if income.is_variable else 0
    
    # Calculate averages
    last_30_days = timezone.now() - timezone.timedelta(days=30)
    last_90_days = timezone.now() - timezone.timedelta(days=90)
    
    transactions_30d = income_transactions.filter(date__gte=last_30_days)
    transactions_90d = income_transactions.filter(date__gte=last_90_days)
    
    avg_30d = sum(t.amount for t in transactions_30d) / 30 * 7 if transactions_30d else 0  # Weekly average
    avg_90d = sum(t.amount for t in transactions_90d) / 90 * 7 if transactions_90d else 0  # Weekly average
    
    context = {
        'income': income,
        'income_transactions': income_transactions[:20],  # Limit to 20 most recent
        'current_period_income': current_period_income,
        'expected_income': expected_income,
        'difference': difference,
        'avg_30d': avg_30d,
        'avg_90d': avg_90d,
        'total_income': sum(t.amount for t in income_transactions),
        'transaction_count': income_transactions.count()
    }
    
    return render(request, 'budgetapp/income_detail.html', context)

from django.contrib import admin
from .models import Budget, Income, Transaction, RecurringTransaction

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'frequency', 'rollover', 'user')
    list_filter = ('frequency', 'rollover', 'user')
    search_fields = ('category', 'user__username')

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('source', 'amount', 'frequency', 'user')
    list_filter = ('frequency', 'user')
    search_fields = ('source', 'user__username')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'budget', 'date', 'user')
    list_filter = ('budget', 'date', 'user')
    search_fields = ('description', 'budget__category', 'user__username')
    date_hierarchy = 'date'

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'budget', 'frequency', 'start_date', 'end_date', 'active', 'user')
    list_filter = ('frequency', 'active', 'budget', 'user')
    search_fields = ('description', 'budget__category', 'user__username')
    date_hierarchy = 'start_date'

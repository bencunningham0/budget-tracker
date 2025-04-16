from django.core.management.base import BaseCommand
from budgetapp.models import Budget, BudgetPeriod
from datetime import datetime
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recompute and store historical budget period data for all budgets using BudgetPeriod model.'

    def handle(self, *args, **options):
        budgets = Budget.objects.all()
        total_created = 0
        for budget in budgets:
            # Remove old periods for a clean recompute
            BudgetPeriod.objects.filter(budget=budget).delete()
            # Recompute periods using the existing method
            periods = budget.get_historical_periods(num_periods=52)
            for period in periods:
                try:
                    start_date = period['start_date']
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_date = period['end_date']
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                except Exception as e:
                    self.stderr.write(f"Skipping period for budget {budget.id} due to date error: {e}")
                    continue
                BudgetPeriod.objects.create(
                    budget=budget,
                    start_date=start_date,
                    end_date=end_date,
                    budget_amount=Decimal(str(period.get('budget_amount', budget.amount))),
                    total_spent=Decimal(str(period.get('total_spent', 0))),
                    difference=Decimal(str(period.get('difference', 0))),
                    is_current=period.get('is_current', False),
                    is_over_budget=period.get('is_over_budget', False),
                )
                total_created += 1
        self.stdout.write(self.style.SUCCESS(f'Recomputed and stored {total_created} budget periods for all budgets.'))

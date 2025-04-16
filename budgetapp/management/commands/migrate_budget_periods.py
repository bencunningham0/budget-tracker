from django.core.management.base import BaseCommand
from budgetapp.models import Budget, BudgetPeriod
from datetime import datetime
from decimal import Decimal

class Command(BaseCommand):
    help = 'Migrate Budget.historical_periods JSONField data to BudgetPeriod model.'

    def handle(self, *args, **options):
        count = 0
        for budget in Budget.objects.all():
            periods = budget.historical_periods or []
            for period in periods:
                # Parse dates safely
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
                # Create BudgetPeriod
                BudgetPeriod.objects.get_or_create(
                    budget=budget,
                    start_date=start_date,
                    end_date=end_date,
                    defaults={
                        'budget_amount': Decimal(str(period.get('budget_amount', budget.amount))),
                        'total_spent': Decimal(str(period.get('total_spent', 0))),
                        'difference': Decimal(str(period.get('difference', 0))),
                        'is_current': period.get('is_current', False),
                        'is_over_budget': period.get('is_over_budget', False),
                    }
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Migrated {count} budget periods to BudgetPeriod model."))

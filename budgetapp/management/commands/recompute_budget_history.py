from django.core.management.base import BaseCommand
from budgetapp.models import Budget
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Recompute and store historical budget period data for all budgets.'

    def handle(self, *args, **options):
        budgets = Budget.objects.all()
        self.stdout.write(f'Recomputing historical data for {budgets.count()} budgets...')
        for budget in tqdm(budgets):
            # This will update total_spent, avg_weekly_spent, and historical_periods
            from budgetapp.models import update_budget_aggregates
            update_budget_aggregates(budget)
        self.stdout.write(self.style.SUCCESS('Historical data recomputed for all budgets.'))

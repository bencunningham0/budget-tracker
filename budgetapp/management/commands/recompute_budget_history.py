from django.core.management.base import BaseCommand
from budgetapp.models import Budget

class Command(BaseCommand):
    help = 'Recompute and store historical budget period data for all budgets.'

    def handle(self, *args, **options):
        budgets = Budget.objects.all()
        for budget in budgets:
            from budgetapp.models import update_budget_aggregates
            update_budget_aggregates(budget)
        self.stdout.write(self.style.SUCCESS('Historical data recomputed for all budgets.'))

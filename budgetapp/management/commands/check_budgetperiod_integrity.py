from django.core.management.base import BaseCommand
from budgetapp.models import Budget, BudgetPeriod
from decimal import Decimal
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check integrity of BudgetPeriod records for all budgets.'

    def handle(self, *args, **options):
        errors = 0
        for budget in Budget.objects.all():
            # Get expected periods from calculation
            expected_periods = budget.get_historical_periods(num_periods=52)
            # Get actual periods from DB
            actual_periods = list(BudgetPeriod.objects.filter(budget=budget).order_by('-start_date'))
            if len(expected_periods) != len(actual_periods):
                self.stdout.write(self.style.ERROR(f"Budget {budget.id} ({budget.category}): Period count mismatch (expected {len(expected_periods)}, found {len(actual_periods)})"))
                errors += 1
                continue
            for i, (expected, actual) in enumerate(zip(expected_periods, actual_periods)):
                mismatches = []
                for field in ['start_date', 'end_date', 'budget_amount', 'total_spent', 'difference', 'is_current', 'is_over_budget']:
                    exp_val = expected[field]
                    act_val = getattr(actual, field)
                    # For decimals, compare as strings to avoid float issues
                    if isinstance(exp_val, Decimal):
                        exp_val = str(exp_val)
                        act_val = str(act_val)
                    if exp_val != act_val:
                        mismatches.append(f"{field}: expected {exp_val}, got {act_val}")
                if mismatches:
                    self.stdout.write(self.style.ERROR(f"Budget {budget.id} ({budget.category}) period {i+1}:\n  " + "\n  ".join(mismatches)))
                    errors += 1
        if errors == 0:
            self.stdout.write(self.style.SUCCESS("All BudgetPeriod records are correct!"))
        else:
            self.stdout.write(self.style.WARNING(f"{errors} mismatches found. Run 'recompute_budget_history' to fix."))

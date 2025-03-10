from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from budgetapp.models import UserProfile

class Command(BaseCommand):
    help = 'Creates user profiles for any users that do not have one'

    def handle(self, *args, **options):
        users_without_profiles = []
        profiles_created = 0
        
        for user in User.objects.all():
            try:
                # Check if the profile exists by trying to access it
                user.profile
            except UserProfile.DoesNotExist:
                # Profile doesn't exist, add user to list
                users_without_profiles.append(user)
                
        if not users_without_profiles:
            self.stdout.write(self.style.SUCCESS('All users already have profiles.'))
            return
            
        self.stdout.write(f'Found {len(users_without_profiles)} users without profiles.')
        
        # Create profiles for users that don't have one
        for user in users_without_profiles:
            UserProfile.objects.create(user=user)
            profiles_created += 1
            self.stdout.write(f'Created profile for user: {user.username}')
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created {profiles_created} user profiles.'))
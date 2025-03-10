import pytz
from django.utils import timezone
from .models import UserProfile

class TimezoneMiddleware:
    """
    Middleware to set the timezone for each request based on user preferences.
    This ensures all datetime objects are displayed in the user's chosen timezone.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get or create user profile to ensure timezone is available
            try:
                profile = request.user.profile
                # Set the timezone for this request
                tzname = profile.timezone
                if tzname:
                    timezone.activate(pytz.timezone(tzname))
            except (AttributeError, UserProfile.DoesNotExist):
                # If profile doesn't exist, use default timezone
                timezone.deactivate()
        else:
            # For anonymous users, use the default timezone
            timezone.deactivate()
        
        response = self.get_response(request)
        return response
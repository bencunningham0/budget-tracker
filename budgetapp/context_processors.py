from django.utils import timezone

def timezone_info(request):
    """
    Context processor that adds the current timezone to all templates
    """
    return {
        'current_timezone': timezone.get_current_timezone_name(),
        'is_dst': timezone.localtime().dst().seconds > 0,
    }
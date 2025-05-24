# core/middleware.py

from django.utils import translation
import locale


class EnglishCurrencyMiddleware:
    """
    Middleware to ensure currency is always displayed in English numerals
    regardless of the selected language.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the original locale
        original_locale = locale.getlocale(locale.LC_NUMERIC)

        try:
            # Force English locale for numeric formatting
            locale.setlocale(locale.LC_NUMERIC, ('en_US', 'UTF-8'))
        except locale.Error:
            try:
                # Fallback if en_US is not available
                locale.setlocale(locale.LC_NUMERIC, 'C')
            except locale.Error:
                # Last resort fallback
                pass

        # Process the request
        response = self.get_response(request)

        # Restore original locale if possible
        try:
            locale.setlocale(locale.LC_NUMERIC, original_locale)
        except (locale.Error, TypeError):
            # If restoration fails, just leave it as is
            pass

        return response
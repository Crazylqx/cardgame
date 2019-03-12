from django.core.cache import cache

cache.delete_pattern('user.*')
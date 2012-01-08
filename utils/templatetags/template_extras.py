from django import template
from utils  import misc_functions

register = template.Library()
register.filter('format_decimal', misc_functions.format_decimal)
register.filter('format_dollar_amount', misc_functions.format_dollar_amount)
register.filter('format_date', misc_functions.format_date)
register.filter('format_date_time', misc_functions.format_date_time)

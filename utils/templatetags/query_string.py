from django                  import template
from django.utils.safestring import mark_safe

import datetime

register = template.Library()

def is_quoted_string(s):
  return (len(s) > 0 and s[0] == s[-1] and s[0] in ('"', "'"))

@register.tag
def query_string(parser, token):
    """
    Allows you to manipulate the query string of a page by adding and removing keywords.
    If a given value is a context variable it will resolve it.
    Based on similiar snippet by user "dnordberg".

    requires you to add:

    TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    )

    to your django settings.

    Usage:
    http://www.url.com/{% query_string "param_to_add=value, param_to_add=value" "param_to_remove, params_to_remove" %}

    Example:
    http://www.url.com/{% query_string "" "filter" %}filter={{new_filter}}
    http://www.url.com/{% query_string "page=page_obj.number" "sort" %}

    """
    try:
        tag_name, add_string, remove_string = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires two arguments" % token.contents.split()[0]
    if not is_quoted_string(add_string) or not is_quoted_string(remove_string):
        raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    add = string_to_dict_of_lists(add_string[1:-1])
    remove = string_to_list(remove_string[1:-1])

    return QueryStringNode(add, remove)

class QueryStringNode(template.Node):
    def __init__(self, add, remove):
        self.add = add
        self.remove = remove

    def render(self, context):
        p = {}
        for k, v in context["request"].GET.lists():
            p[k] = v

        return get_query_string(p, self.add, self.remove, context)

def get_query_string(p, new_params, remove, context):
    """
    Add and remove query parameters. Adapted from `django.contrib.admin`.
    """
    for r in remove:
        if r in p:
            del p[r]

    for k, v in new_params.items():
        if k in p and v is None:
            del p[k]
        elif v is not None:
            p[k] = v

    pairs = []
    for k, vl in p.items():
        for v in vl:
            try:
                v = template.Variable(v).resolve(context)
            except:
                pass
            pairs.append(u'%s=%s' % (k, v))

    return mark_safe('?' + '&amp;'.join(pairs).replace(' ', '%20'))


# Adapted from lib/utils.py

def string_to_dict_of_lists(s):
    d = {}
    for arg in str(s).split(','):
        arg = arg.strip()
        if arg == '': continue
        key, val = arg.split('=', 1)
        if key in d:
            d[key].append(val)
        else:
            d[key] = [val]
    return d

def string_to_list(s):
    args = []
    for arg in str(s).split(','):
        arg = arg.strip()
        if arg == '': continue
        args.append(arg)
    return args

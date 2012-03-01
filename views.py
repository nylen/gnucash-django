from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.db.models               import F, Q
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split, Lock, Rule, RuleAccount

from decimal import Decimal

import json

import filters
import forms
import settings


@login_required
def index(request):
  template = loader.get_template('index.html')
  accounts = [Account.from_path(path) for path in settings.ACCOUNTS_LIST]

  c = RequestContext(request, {
    'accounts': accounts,
    'show_account_links': True,
  })
  return HttpResponse(template.render(c))


@login_required
def account(request, index):
  template = loader.get_template('account_details.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  splits = filters.TransactionSplitFilter(account)

  choices = forms.AccountChoices(account)

  filter_form = forms.FilterForm(choices, request.GET)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  splits.order_filtered_splits()

  modify_form_data = request.GET.copy()
  modify_form_data['save_rule'] = True
  modify_form = forms.ModifyForm(choices, modify_form_data, auto_id="modify_id_%s")

  try:
    page_num = int(request.GET.get('page'))
  except:
    page_num = 1

  items_per_page = 50
  pages = Paginator(splits.filtered_splits, items_per_page)

  try:
    page = pages.page(page_num)
  except PageNotAnInteger:
    page = pages.page(1)
  except EmptyPage:
    page = pages.page(pages.num_pages)

  c = RequestContext(request, {
    'any_filters_applied': splits.any_filters_applied,
    'opposing_account_filter_applied': splits.opposing_account_filter_applied,
    'regex_chars_js': json.dumps(filters.TransactionSplitFilter.REGEX_CHARS),
    'accounts_js': json.dumps(choices.accounts_dict),
    'num_transactions_js': json.dumps(page.paginator.count),
    'account': account,
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
  })
  return HttpResponse(template.render(c))


@login_required
def modify(request, index):
  template = loader.get_template('modify.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  splits = filters.TransactionSplitFilter(account)

  errors = False

  choices = forms.AccountChoices(account)

  opposing_account_guid = request.POST['change_opposing_account']
  opposing_account = None
  try:
    opposing_account = Account.objects.get(guid=opposing_account_guid)
  except Account.DoesNotExist:
    errors = "Account '%s' not found." % opposing_account_guid

  form_data = request.POST.copy()

  min_amount = None
  max_amount = None

  modified_transactions = False
  tx_count = 0

  if not errors:
    modify_form = forms.ModifyForm(choices, request.POST)
    if modify_form.is_valid():
      splits.filter_splits(modify_form.cleaned_data)

      min_amount = modify_form.cleaned_data['min_amount']
      max_amount = modify_form.cleaned_data['max_amount']
      if min_amount is None:
        min_amount = 0
      elif min_amount < 0:
        raise ValueError('min_amount (%s) < 0' % min_amount)
      if max_amount is None:
        max_amount = 0
      elif max_amount < 0:
        raise ValueError('max_amount (%s) < 0' % max_amount)
      if min_amount > max_amount:
        raise ValueError('min_amount (%s) > max_amount (%s)' % (min_amount, max_amount))

      tx_count = splits.filtered_splits.count()
      if tx_count > 0:
        tx_guids = splits.filtered_splits.distinct().values('transaction__guid')
        splits_real = Split.objects.filter(transaction__guid__in=tx_guids).exclude(account=account)

        # ugh
        if min_amount: min_amount -= Decimal('1e-8')
        if max_amount: max_amount += Decimal('1e-8')

        if min_amount and max_amount:
          splits_real = splits_real.filter(
            (Q(value_num__gte=F('value_denom') *  min_amount) & Q(value_num__lte=F('value_denom') *  max_amount)) |
            (Q(value_num__lte=F('value_denom') * -min_amount) & Q(value_num__gte=F('value_denom') * -max_amount)))
        elif min_amount:
          splits_real = splits_real.filter(
            (Q(value_num__gte=F('value_denom') *  min_amount)) |
            (Q(value_num__lte=F('value_denom') * -min_amount)))
        elif max_amount:
          splits_real = splits_real.filter(
            (Q(value_num__lte=F('value_denom') *  max_amount)) |
            (Q(value_num__gte=F('value_denom') * -max_amount)))

        split_guids = list(splits_real.distinct().values_list('guid', flat=True))
        tx_count = len(split_guids)

        if tx_count > 0:
          Lock.obtain()
          Split.objects.filter(guid__in=split_guids).update(account=opposing_account)
          Lock.release()
          form_data['opposing_accounts'] = opposing_account_guid
          modified_transactions = True

      if modify_form.cleaned_data['save_rule']:
        if splits.tx_desc:
          rule = Rule()
          rule.opposing_account_guid = opposing_account_guid
          rule.match_tx_desc = splits.tx_desc
          rule.is_regex = splits.tx_desc_is_regex
          if min_amount: rule.min_amount = min_amount
          if max_amount: rule.max_amount = max_amount
          rule.save()

          rule_account = RuleAccount()
          rule_account.rule = rule
          rule_account.account_guid = account.guid
          rule_account.save()

        else:
          errors = 'Cannot save rule with no description filter.'

    else:
      # modify_form is not valid
      errors = str(modify_form.errors)

  hidden_filter_form = forms.HiddenFilterForm(choices, form_data)

  c = RequestContext(request, {
    'account': account,
    'opposing_account': opposing_account,
    'hidden_filter_form': hidden_filter_form,
    'errors': errors,
    'modified_transactions': modified_transactions,
    'tx_count': tx_count,
  })
  return HttpResponse(template.render(c))

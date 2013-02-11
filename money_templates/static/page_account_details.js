$(function() {
  var currentForm = null;

  $.fn.focusselect = function(delay) {
    var o = this;
    var fn = function() {
      o.each(function() {
        this.focus();
        this.select();
      });
    };
    if (delay) {
      window.setTimeout(fn, delay);
    } else {
      fn();
    }
  };

  $('#form-links').show();
  $('#forms .form').hide().removeClass('block block-first');
  $('#form-filters tr.field-opposing_account').show();
  $('#form-filters tr.field-opposing_accounts').each(function() {
    $(this).find('ul').hide();
    $(this).hide();
  });

  var delayFilterFocus = true;

  function showFilterForm(slow) {
    if (!$('#form-filters').is(':visible')) {
      if (!slow) {
        $('#form-filters').show();
      }
      delayFilterFocus = false;
      $('#toggle-filters').trigger('click');
      delayFilterFocus = true;
    }
  }

  $('#forms a.toggle-form').click(function() {
    var form = $(this).data('form');
    var $form = $('#form-' + form);
    if (form == currentForm) {
      $form.slideUp();
      currentForm = null;
    } else {
      $form.insertAfter('#before-forms').slideDown();
      $('#forms .form').not($form).slideUp();
      currentForm = form;
    }
    if (currentForm == form) {
      $('#form-links a').not(this).removeClass('active');
      $(this).addClass('active');
    } else {
      $(this).removeClass('active');
    }
    return false;
  });

  $('#toggle-filters').click(function() {
    $('#id_tx_desc').focusselect(delayFilterFocus ? 250 : 0);
  });

  if (filteringAny) {
    showFilterForm();
  }

  var $checkboxes = $('#form-filters tr.field-opposing_accounts :checkbox');

  $('#form-filters form').submit(function(e) {
    if ($('#id_opposing_accounts_0').is(':checked')) {
      $checkboxes.attr('checked', false);
    }
    return true;
  });

  $('#form-filters tr.field-opposing_accounts li').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#id_opposing_accounts_0'
  });

  $('#forms :text').attr('autocomplete', 'off').selectfocus();


  $('#filter-multi-accounts').click(function() {
    $('#single-opposing-account').unbind('change').remove();
    $('#form-filters tr.field-opposing_account').hide();
    $('#form-filters tr.field-opposing_accounts').each(function() {
      $(this).show();
      $('ul', this).slideDown();
    });
    return false;
  });

  $checkboxes.each(function() {
    $('#single-opposing-account').append(
      '<option value="' + $(this).val() + '">' + $(this).closest('label').text() + '</select>');
  });

  $('#single-opposing-account').change(function() {
    var value = $(this).val();
    $checkboxes.attr('checked', function() {
      return (value == 'all' || value == $(this).val());
    });
  });


  var numChecked = $checkboxes.filter(':checked').length;

  if (numChecked == 1) {
    $('#single-opposing-account').val($checkboxes.filter(':checked').val());
  } else if (numChecked == 0 || numChecked == $checkboxes.length) {
    $('#single-opposing-account').val('all');
    $checkboxes.attr('checked', true);
  } else {
    $('#form-filters tr.field-opposing_accounts ul').show();
    $('#filter-multi-accounts').trigger('click');
  }

  // from http://simonwillison.net/2006/Jan/20/escape/
  RegExp.escape = function(text) {
    //return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    return text.replace(/[-[\]{}()*+?.,\\^$|#]/g, "\\$&");
  }

  var formatDate = function(date) {
    if (isNaN(date)) {
      return '';
    } else {
      var m = '00' + (date.getMonth() + 1);
      var d = '00' + date.getDate();
      var y = '00' + date.getFullYear();
      return (m.substring(m.length - 2)
        + '/' + d.substring(d.length - 2)
        + '/' + y.substring(y.length - 2));
    }
  }

  $('table.transactions td.description').click(function() {
    showFilterForm(true);

    var thisValue = $(this).data('value');
    var txDesc = $('#id_tx_desc').val();

    for (i in regexChars) {
      var c = regexChars.charAt(i);
      if (thisValue.indexOf(c) >= 0) {
        thisValue = RegExp.escape(thisValue);
        break;
      }
    }

    $('#id_tx_desc').val(thisValue == txDesc ? '' : thisValue)
      .css('visibility', 'visible') // Android ICS browser hack
      .focusselect();
  });

  $('table.transactions a.search').click(function(e) {
    e.stopPropagation();
    return true;
  });

  $('table.transactions td.date').click(function() {
    showFilterForm(true);

    var thisDate = new Date(Date.parse($(this).data('value')));
    var minDate  = new Date(Date.parse($('#id_min_date').val()));
    var maxDate  = new Date(Date.parse($('#id_max_date').val()));
    var toFocus = '#id_min_date';

    if (thisDate < minDate) {
      minDate = thisDate;
    } else if (thisDate > maxDate) {
      toFocus = '#id_max_date';
      maxDate = thisDate;
    } else if (thisDate - minDate == 0 && thisDate - maxDate == 0) {
      // Can't use == to compare dates
      minDate = NaN;
      maxDate = NaN;
    } else {
      minDate = thisDate;
      maxDate = thisDate;
    }
    $('#id_min_date').val(formatDate(minDate));
    $('#id_max_date').val(formatDate(maxDate));
    // Hack to make the Android ICS browser actually display the new value
    $('#id_min_date, #id_max_date').css('visibility', 'visible');

    $(toFocus).focusselect();
  });


  $('#form-modify form').submit(function(e) {
    if (!$('#modify_id_change_opposing_account').val()) {
      alert('Select an opposing account first.');
      return false;
    }
    if (numTransactions > 100) {
      return confirm('This action may affect more than 100 '
        + 'transactions.  Are you sure you want to continue?');
    }
  });


  $('td.memo').each(function() {
    $(this).html('<span class="edit-memo"></span>')
    .find('.edit-memo').text($(this).data('value'));
  });

  $('.add-memo').show().click(function() {
    var $memoRow = $(this).closest('tr').next('tr');
    var $memoCell;
    while (($memoCell = $memoRow.find('.memo')).length) {
      var memo = $memoCell.data('value');
      if (!memo) {
        $memoRow.removeClass('hidden');
        $memoCell.find('.edit-memo').trigger('click');
        return false;
      }
      $memoRow = $memoRow.next('tr');
    }
    alert("Cannot add a memo to any of this transaction's splits.");
    return false;
  });

  $('.edit-memo').click(function() {
    var $a = $(this);
    if ($a.hasClass('loading')) {
      return false;
    }
    var account = accounts[$a.closest('tr').data('account')];
    var oldMemo = $a.closest('.memo').data('value');
    $a.addClass('editing').text('Editing...');
    memo = prompt("Enter memo (associated with account '" + account.path + "'):", oldMemo);
    $a.removeClass('editing');
    if (memo == null) {
      $a.text(oldMemo);
    } else {
      $a.addClass('loading').text('Setting memo...');
      $a.closest('.memo').data('value', memo);
      $.ajax({
        url: apiFunctionUrls['change_memo'],
        type: 'POST',
        headers: {
          'X-CSRFToken': $.cookie('csrftoken')
        },
        data: {
          'split_guid': $a.closest('tr').data('split'),
          'memo': memo
        },
        cache: false,
        success: function(d) {
          $a.text(d.memo || d.error || 'Unknown error');
        },
        error: function(xhr, status, e) {
          $a.text('Error: ' + e);
        },
        complete: function(xhr, status) {
          $a.removeClass('loading');
        }
      });
    }
    return false;
  });

  var $select = $('.change-account');

  $('.change-opposing-account').each(function() {
    $select.clone().prependTo(this).val($(this).data('value'));
  }).show()
  .find('.change-account').show()
  .change(function() {
    var $a = $(this).closest('.change-opposing-account');
    var $name = $a.prev('.opposing-account-name');
    var oldAccountKey = $(this).closest('.change-opposing-account').data('value');
    var newAccountKey = $(this).val();
    if (newAccountKey != oldAccountKey) {
      $name.addClass('loading').text('Setting account...');
      $a.data('value', newAccountKey);
      $.ajax({
        url: apiFunctionUrls['change_account'],
        type: 'POST',
        headers: {
          'X-CSRFToken': $.cookie('csrftoken')
        }, data: {
          'split_guid': $a.closest('tr').data('opposing-split'),
          'account_guid': newAccountKey
        },
        cache: false,
        success: function(d) {
          var account = accounts[d.account_guid];
          $name.text((account && account.name) || d.error || 'Unknown error');
        }, error: function(xhr, status, e) {
          $a.text('Error: ' + e);
        },
        complete: function(xhr, status) {
          $a.removeClass('loading');
        }
      });
    }
  });

  $select.remove();


  // The Android ICS browser doesn't seem to give disabled/readonly input
  // fields any special styling.  Apply some manually.
  if (navigator.userAgent.toLowerCase().indexOf('android') >= 0) {
    $('input.disabled, input.readonly').css('backgroundColor', '#ddd');
  }

  // Resize textboxes and select elements up to a maximum width.
  var windowWidth = $(window).width();
  if (windowWidth >= 800) {
    var maxWidths = {
      'input': 450,
      'select': 250
    };
    $('table.form-table').each(function() {
      var dims = $(this).hiddenDimensions();
      var widthUncapped = windowWidth - dims.width - 20;
      $('input:text, select', this).each(function() {
        var width = Math.min(
          widthUncapped,
          maxWidths[this.nodeName.toLowerCase()]);
        $(this).css({
          'width': width,
          'maxWidth': width
        });
      });
    });
  }
});

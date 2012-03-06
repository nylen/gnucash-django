$(function() {
  var currentForm = null;

  $('#form-links').show();
  $('#forms .form').hide().removeClass('block block-first');
  $('#form-filters tr.field-opposing_account').show();
  $('#form-filters tr.field-opposing_accounts').each(function() {
    $(this).find('ul').hide();
    $(this).hide();
  });

  function showFilterForm(slow) {
    if (!$('#form-filters').is(':visible')) {
      if (!slow) {
        $('#form-filters').show();
      }
      $('#toggle-filters').trigger('click');
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
    $('#id_tx_desc').each(function() {
      this.focus();
      this.select();
    });
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

  $('#form-filters input[name=opposing_accounts]').each(function() {
    var guid = $(this).val();
    if (guid in accounts) {
      $(this).closest('label').attr('title', accounts[guid].path);
    }
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
      .each(function() {
        this.focus();
        this.select();
      });
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

    $(toFocus).each(function() {
      this.focus();
      this.select();
    });
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

$(function() {
  var currentForm = null;

  $('#forms a.toggle-form').data('visible', false).click(function() {
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


  var $checkboxes = $('#form-filters tr.field-opposing_accounts :checkbox');

  $('#clear-filters').click(function() {
    $('#form-filters input[type=text], select').val('');
    $checkboxes.attr('checked', false);
    $('#form-filters form').submit();
  });

  $('#form-filters tr.field-opposing_accounts li').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#id_opposing_accounts_0'
  });

  $('#form-filters :text').selectfocus();


  $('#filter-multi-accounts').click(function() {
    $('#single-opposing-account').unbind('change').remove();
    $(this).parents('tr').hide().next('tr').each(function() {
      $(this).add('#all-opposing-accounts-container').show();
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
    $('#filter-multi-accounts').trigger('click');
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

  $('table.transactions td.date').click(function() {
    if ($('#form-filters').is(':visible')) {
      var thisDate = new Date(Date.parse($(this).text()));
      var minDate  = new Date(Date.parse($('#id_min_date').val()));
      var maxDate  = new Date(Date.parse($('#id_max_date').val()));
      if (thisDate < minDate) {
        minDate = thisDate;
      } else if (thisDate > maxDate) {
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
    }
  });
});

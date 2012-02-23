$(function() {
  $('#show-filters').click(function() {
    $(this).hide();
    $('#filters').slideDown();
  });

  $('#clear-filters').click(function() {
    $('#filters input[type=text], select').val('');
    $('#filters').submit();
  });
});

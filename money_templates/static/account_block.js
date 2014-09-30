$(function() {
  $('body').on('click', '.account-balance-info', function(e) {
    alert($(this).find('.balance-title').attr('title'));
    return false;
  });
});

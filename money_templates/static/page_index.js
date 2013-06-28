$(function() {
  $('#select-accounts li').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#accounts-all'
  });
  $('#select-accounts li a').click(function() {
    location.href = this.href;
    return true;
  });
});

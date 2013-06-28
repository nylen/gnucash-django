function matchesInitials(initials, strings) {
  if (initials == '') {
    return true;
  }
  if (!strings.length) {
    return false;
  }
  for (var i = 1; ; i++) {
    if (strings[0].substring(0, i) == initials.substring(0, i)) {
      if (matchesInitials(initials.substring(i), strings.slice(1))) {
        return true;
      }
    } else {
      break;
    }
  }
  return false;
}

$(function() {
  $('select.change-account, .change-account-container select').select2({
    matcher: function(term, text) {
      term = term.toLowerCase();
      text = text.toLowerCase();
      if (text.indexOf(term) >= 0) {
        return true;
      }
      if (matchesInitials(term, text.split(':'))) {
        return true;
      }
      return false;
    },
    width: '400px'
  });
});

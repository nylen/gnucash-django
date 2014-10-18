$(function() {
  $('.close-window').click(function() {
    window.close();
  });

  $('.delete-attachment').click(function() {
    return confirm('Are you sure you want to delete this attachment?');
  });
});

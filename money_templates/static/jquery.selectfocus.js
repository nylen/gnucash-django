/* SelectFocus jQuery plugin
 *
 * Copyright (C) 2011 James Nylen
 *
 * Released under MIT license
 * For details see:
 * https://github.com/nylen/selectfocus
 */

(function($) {
  var ns = '.selectfocus';
  var dataKey = 'lastEvent' + ns;

  /* It seems like just calling select() from a focus event handler SHOULD be
   * enough:
   *
   *   $('selector').focus(function() { this.select(); });
   *
   * However, Chrome and Safari have a bug that causes this not to work -
   * clicking on a textbox, clicking off of it, then clicking back onto its
   * text causes the cursor to appear at the point in the text where the
   * textbox was clicked.
   *
   * See http://code.google.com/p/chromium/issues/detail?id=4505 for details.
   *
   * Recent versions of Firefox (4.x+?) appear to have the same issue, but it
   * only appears once every two clicks.  Very strange.
   *
   * To work around this, we look for the following sequence of events in a
   * particular text box:
   *
   *   mousedown -> focus -> mouseup ( -> click )
   *
   * If we get that chain of events, call preventDefault() in the mouseup event
   * handler as suggested on the Chromium bug page.  This fixes the issue in
   * both Webkit and Firefox.  In IE, we also need to call this.select() in the
   * click event handler.
   */

  var functions = {
    mousedown: function(e) {
      $(this).data(dataKey, 'mousedown');
    },

    focus: function(e) {
      $(this).data(dataKey,
        ($(this).data(dataKey) == 'mousedown' ? 'focus' : ''));

      this.select();
    },

    mouseup: function(e) {
      if($(this).data(dataKey) == 'focus') {
        e.preventDefault();
      }

      $(this).data(dataKey,
        ($(this).data(dataKey) == 'focus' ? 'mouseup' : ''));
    },

    click: function() {
      if($(this).data(dataKey) == 'mouseup') {
        this.select();
      }

      $(this).data(dataKey, 'click');
    },

    blur: function(e) {
      // Just for good measure
      $(this).data(dataKey, 'blur');
    }
  };

  $.fn.selectfocus = function(opts) {
    var toReturn = this.noselectfocus();
    $.each(functions, function(e, fn) {
      toReturn = toReturn[opts && opts.live ? 'live' : 'bind'](e + ns, fn);
    });
    return toReturn;
  };

  $.fn.noselectfocus = function() {
    var toReturn = this;
    // .die('.namespace') does not appear to work in jQuery 1.5.1 or 1.6.2.
    // Loop through events one at a time.
    $.each(functions, function(e, fn) {
      toReturn = toReturn.die(e + ns, fn);
    });
    return toReturn.unbind(ns).removeData(dataKey);
  };
})(jQuery);

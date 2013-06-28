/* ShiftCheckbox jQuery plugin
 *
 * Copyright (C) 2011-2012 James Nylen
 *
 * Released under MIT license
 * For details see:
 * https://github.com/nylen/shiftcheckbox
 *
 * Requires jQuery v1.6 or higher.
 */

(function($) {
  var ns = '.shiftcheckbox';

  $.fn.shiftcheckbox = function(opts) {
    opts = $.extend({
      checkboxSelector: null,
      selectAll: null
    }, opts);

    var $containers;
    var $checkboxes;
    var $containersSelectAll;
    var $checkboxesSelectAll;
    var $otherSelectAll;
    var $containersAll;
    var $checkboxesAll;

    if (opts.selectAll) {
      // We need to set up a "select all" control
      $containersSelectAll = $(opts.selectAll);
      if ($containersSelectAll && !$containersSelectAll.length) {
        $containersSelectAll = false;
      }
    }

    if ($containersSelectAll) {
      $checkboxesSelectAll = $containersSelectAll
        .filter(':checkbox')
        .add($containersSelectAll.find(':checkbox'));

      $containersSelectAll = $containersSelectAll.not(':checkbox');
      $otherSelectAll = $containersSelectAll.filter(function() {
        return !$(this).find($checkboxesSelectAll).length;
      });
      $containersSelectAll = $containersSelectAll.filter(function() {
        return !!$(this).find($checkboxesSelectAll).length;
      }).each(function() {
        $(this).data('childCheckbox', $(this).find($checkboxesSelectAll)[0]);
      });
    }

    if (opts.checkboxSelector) {

      // checkboxSelector means that the elements we need to attach handlers to
      // ($containers) are not actually checkboxes but contain them instead

      $containersAll = this.filter(function() {
        return !!$(this).find(opts.checkboxSelector).filter(':checkbox').length;
      }).each(function() {
        $(this).data('childCheckbox', $(this).find(opts.checkboxSelector).filter(':checkbox')[0]);
      }).add($containersSelectAll);

      $checkboxesAll = $containersAll.map(function() {
        return $(this).data('childCheckbox');
      });

    } else {

      $checkboxesAll = this.filter(':checkbox');

    }

    if ($checkboxesSelectAll && !$checkboxesSelectAll.length) {
      $checkboxesSelectAll = false;
    } else {
      $checkboxesAll = $checkboxesAll.add($checkboxesSelectAll);
    }

    if ($otherSelectAll && !$otherSelectAll.length) {
      $otherSelectAll = false;
    }

    if ($containersAll) {
      $containers = $containersAll.not($containersSelectAll);
    }
    $checkboxes = $checkboxesAll.not($checkboxesSelectAll);

    if (!$checkboxes.length) {
      return;
    }

    var lastIndex = -1;

    var checkboxClicked = function(e) {
      var checked = !!$(this).attr('checked');

      var curIndex = $checkboxes.index(this);
      if (curIndex < 0) {
        if ($checkboxesSelectAll.filter(this).length) {
          $checkboxesAll.attr('checked', checked);
        }
        return;
      }

      if (e.shiftKey && lastIndex != -1) {
        var di = (curIndex > lastIndex ? 1 : -1);
        for (var i = lastIndex; i != curIndex; i += di) {
          $checkboxes.eq(i).attr('checked', checked);
        }
      }

      if ($checkboxesSelectAll) {
        if (checked && !$checkboxes.not(':checked').length) {
          $checkboxesSelectAll.attr('checked', true);
        } else if (!checked) {
          $checkboxesSelectAll.attr('checked', false);
        }
      }

      lastIndex = curIndex;
    };

    if ($checkboxesSelectAll) {
      $checkboxesSelectAll
        .attr('checked', !$checkboxes.not(':checked').length)
        .filter(function() {
          return !$containersAll.find(this).length;
        }).bind('click' + ns, checkboxClicked);
    }

    if ($otherSelectAll) {
      $otherSelectAll.bind('click' + ns, function() {
        var checked;
        if ($checkboxesSelectAll) {
          checked = !!$checkboxesSelectAll.eq(0).attr('checked');
        } else {
          checked = !!$checkboxes.eq(0).attr('checked');
        }
        $checkboxesAll.attr('checked', !checked);
      });
    }

    if (opts.checkboxSelector) {
      $containersAll.bind('click' + ns, function(e) {
        var $checkbox = $($(this).data('childCheckbox'));
        $checkbox.not(e.target).attr('checked', function() {
          return !$checkbox.attr('checked');
        });

        $checkbox[0].focus();
        checkboxClicked.call($checkbox, e);

        // If the user clicked on a label inside the row that points to the
        // current row's checkbox, cancel the event.
        var $label = $(e.target).closest('label');
        var labelFor = $label.attr('for');
        if (labelFor && labelFor == $checkbox.attr('id')) {
          if ($label.find($checkbox).length) {
            // Special case:  The label contains the checkbox.
            if ($checkbox[0] != e.target) {
              return false;
            }
          } else {
            return false;
          }
        }
      }).bind('mousedown' + ns, function(e) {
        if (e.shiftKey) {
          // Prevent selecting text by Shift+click
          return false;
        }
      });
    } else {
      $checkboxes.bind('click' + ns, checkboxClicked);
    }

    return this;
  };
})(jQuery);

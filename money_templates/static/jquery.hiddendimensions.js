// from http://www.foliotek.com/devblog/getting-the-width-of-a-hidden-element-with-jquery-using-width/
(function($) {
  $.fn.hiddenDimensions = function(includeMargin) {
    // Optional parameter includeMargin is used when calculating outer dimensions
    var $item = this;
    var props = {
      position: 'absolute',
      visibility: 'hidden',
      display: 'block'
    };
    var dim = {
      width:0,
      height:0,
      innerWidth: 0,
      innerHeight: 0,
      outerWidth: 0,
      outerHeight: 0
    };
    var $hiddenParents = $item.parents().andSelf().not(':visible');
    var includeMargin = (includeMargin == null ? false : includeMargin);

    var oldProps = [];
    $hiddenParents.each(function() {
      var old = {};
      for (var name in props) {
        old[name] = this.style[name];
        this.style[name] = props[name];
      }
      oldProps.push(old);
    });

    dim.width = $item.width();
    dim.outerWidth = $item.outerWidth(includeMargin);
    dim.innerWidth = $item.innerWidth();
    dim.height = $item.height();
    dim.innerHeight = $item.innerHeight();
    dim.outerHeight = $item.outerHeight(includeMargin);

    $hiddenParents.each(function(i) {
      var old = oldProps[i];
      for (var name in props) {
        this.style[name] = old[name];
      }
    });

    return dim;
  }
}(jQuery));

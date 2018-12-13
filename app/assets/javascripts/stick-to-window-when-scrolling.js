;(function (global) {
  'use strict';

  var $ = global.jQuery;
  var GOVUK = global.GOVUK || {};

  // Constructor for objects holding data for each element to have sticky behaviour
  var StickyElement = function ($el, sticky) {
    this._sticky = sticky;
    this.$fixedEl = $el;
    this._initialFixedClass = 'content-fixed-onload';
    this._fixedClass = 'content-fixed';
    this._appliedClass = null;
    this._$shim = null;
    this._stopped = false;
  };
  StickyElement.prototype.stickyClass = function () {
    return (this._sticky._initialPositionsSet) ? this._fixedClass : this._initialFixedClass;
  };
  StickyElement.prototype.appliedClass = function () {
    return this._appliedClass;
  };
  StickyElement.prototype.isStuck = function () {
    return this._appliedClass !== null;
  };
  StickyElement.prototype.stick = function () {
    this._appliedClass = this.stickyClass();
    this._hasBeenCalled = true;
  };
  StickyElement.prototype.release = function () {
    this._appliedClass = null;
    this._hasBeenCalled = true;
  };
  // When a sticky element is moved into the 'stuck' state, a shim is inserted into the
  // page to preserve the space the element occupies in the flow.
  StickyElement.prototype.addShim = function (position) {
    this._$shim = $('<div class="shim" style="width: ' + this.horizontalSpace + 'px; height: ' + this.verticalSpace + 'px">&nbsp</div>');
    this.$fixedEl[position](this._$shim);
  };
  StickyElement.prototype.removeShim = function () {
    this._$shim.remove();
    this._$shim = null;
  };
  // Changes to the dimensions of a sticky element with a shim need to be passed on to the shim
  StickyElement.prototype.updateShim = function () {
    if (this._$shim) {
      this._$shim.css({
        'height': this.verticalSpace,
        'width': this.horizontalSpace
      });
    }
  };
  StickyElement.prototype.stop = function () {
    this._stopped = true;
  };
  StickyElement.prototype.unstop = function () {
    this._stopped = false;
  };
  StickyElement.prototype.stopped = function () {
    return this._stopped;
  };

  // Constructor for objects collecting together all generic behaviour for controlling the state of
  // sticky elements
  var Sticky = function (selector) {
    this._hasScrolled = false;
    this._scrollTimeout = false;
    this._hasResized = false;
    this._resizeTimeout = false;
    this._elsLoaded = false;
    this._initialPositionsSet = false;
    this._els = [];

    this.CSS_SELECTOR = selector;
  };
  Sticky.prototype.getWindowDimensions = function () {
    return {
      height: $(global).height(),
      width: $(global).width()
    };
  };
  Sticky.prototype.getWindowPositions = function () {
    return {
      scrollTop: $(global).scrollTop()
    };
  };
  // Change state of sticky elements based on their position relative to the window
  Sticky.prototype.setElementPositions = function () {
    var self = this;

    $.each(self._els, function (i, el) {
      var $el = el.$fixedEl;

      var windowDimensions = self.getWindowDimensions();

      if (self.scrolledFromInsideWindow(el.scrolledFrom)) {
        self.release(el);
      } else {
        if (self.scrolledToOutsideWindow(el, windowDimensions.height)) {
          self.stop(el);
        } else if (self.viewportIsWideEnough(windowDimensions.width)) {
          if (el.stopped) {
            self.unstop(el);
          }
          self.stick(el);
        }
      }
    });

    if (self._initialPositionsSet === false) { self._initialPositionsSet = true; }
  };
  // Store all the dimensions for a sticky element to limit DOM queries
  Sticky.prototype.setElementDimensions = function (el, callback) {
    var self = this;
    var $el = el.$fixedEl;
    var onHeightSet = function () {
      el.scrolledTo = self.getScrollingTo(el);
      // if element is shim'ed, pass changes in dimension on to the shim
      if (el._$shim) {
        el.updateShim();
        $el = el._$shim;
      }
      el.scrolledFrom = self.getScrolledFrom($el);
      if (callback !== undefined) {
        callback();
      }
    };

    this.setElWidth(el);
    this.setElHeight(el, onHeightSet);
  };
  // Recalculate stored dimensions for all sticky elements
  Sticky.prototype.recalculate = function () {
    var self = this;

    $.each(self._els, function (i, el) {
      self.setElementDimensions(el);
    });
    self.setElementPositions();
  };
  Sticky.prototype.setElWidth = function (el) {
    el.horizontalSpace = el.$fixedEl.outerWidth(true);
  };
  Sticky.prototype.setElHeight = function (el, callback) {
    var self = this;
    var $el = el.$fixedEl;
    var $img = $el.find('img');

    if ((!self._elsLoaded) && ($img.length > 0)) {
      var image = new global.Image();
      image.onload = function () {
        el.verticalSpace = $el.outerHeight(true);
        el.height = $el.outerHeight();
        callback();
      };
      image.src = $img.attr('src');
    } else {
      el.verticalSpace = $el.outerHeight(true);
      el.height = $el.outerHeight();
      callback();
    }
  };
  Sticky.prototype.allElementsLoaded = function (totalEls) {
    return this._els.length === totalEls;
  };
  Sticky.prototype.init = function () {
    var self = this;
    var $els = $(self.CSS_SELECTOR);
    var numOfEls = $els.length;

    if (numOfEls > 0) {
      $els.each(function (i, el) {
        var $el = $(el);
        var elObj = new StickyElement($el, self);

        self.setElementDimensions(elObj, function () {
          self._els.push(elObj);
          // set positions based on initial scroll positionu
          if (self._els.length === numOfEls) {
            self._elsLoaded = true;
            self.setElementPositions();
          }
        });
      });

      // flag when scrolling takes place and check (and re-position) sticky elements relative to
      // window position
      if (self._scrollTimeout === false) {
        $(global).scroll(function (e) { self.onScroll(); });
        self._scrollTimeout = global.setInterval(function (e) { self.checkScroll(); }, 50);
      }

      // Recalculate all dimensions when the window resizes
      if (self._resizeTimeout === false) {
        $(global).resize(function (e) { self.onResize(); });
        self._resizeTimeout = global.setInterval(function (e) { self.checkResize(); }, 50);
      }
    }
  };
  Sticky.prototype.onScroll = function () {
    this._hasScrolled = true;
  };
  Sticky.prototype.onResize = function () {
    this._hasResized = true;
  };
  Sticky.prototype.viewportIsWideEnough = function (windowWidth) {
    return windowWidth > 768;
  };
  Sticky.prototype.checkScroll = function () {
    var self = this;

    if (self._hasScrolled === true) {
      self._hasScrolled = false;
      self.setElementPositions(true);
    }
  };
  Sticky.prototype.checkResize = function () {
    var self = this;

    if (self._hasResized === true) {
      self._hasResized = false;

      var windowDimensions = self.getWindowDimensions();

      $.each(self._els, function (i, el) {
        var $el = el.$fixedEl;

        var elResize = $el.hasClass('js-self-resize');
        if (elResize) {
          var $shim = $('.shim');
          var $elParent = $el.parent('div');
          var elParentWidth = $elParent.width();
          $shim.css('width', elParentWidth);
          $el.css('width', elParentWidth);
          self.setElHeight(el);
        }

        if (!self.viewportIsWideEnough(windowDimensions.width)) {
          self.release($el);
        }
      });
    }
  };
  Sticky.prototype.release = function (el) {
    if (el.isStuck()) {
      var $el = el.$fixedEl;

      $el.removeClass(el.appliedClass()).css('width', '');
      el.removeShim();
      el.release();
    }
  };

  // Extension of sticky object to add behaviours specific to sticking to top of window
  var stickAtTop = new Sticky('.js-stick-at-top-when-scrolling');
  // Store top of sticky elements while unstuck
  stickAtTop.getScrolledFrom = function ($el) {
    return $el.offset().top;
  };
  // Store furthest point top of sticky element is allowed
  stickAtTop.getScrollingTo = function (el) {
    var footer = $('.js-footer:eq(0)');
    if (footer.length === 0) {
      return 0;
    }
    return (footer.offset().top - 10) - el.height;
  };
  stickAtTop.scrolledFromInsideWindow = function (scrolledFrom) {
    var windowTop = this.getWindowPositions().scrollTop;

    return scrolledFrom > windowTop;
  };
  stickAtTop.scrolledToOutsideWindow = function (el, windowHeight) {
    var windowTop = this.getWindowPositions().scrollTop;
  
    return windowTop > el.scrolledTo;
  };
  stickAtTop.stick = function (el) {
    if (!el.isStuck()) {
      var $el = el.$fixedEl;

      el.addShim('before');
      // element will be absolutely positioned so cannot rely on parent element for width
      $el.css('width', $el.width() + 'px').addClass(el.stickyClass());
      el.stick();
    }
  };
  stickAtTop.stop = function (el) {
    if (!el.stopped()) {
      el.$fixedEl.css({ 'position': 'absolute', 'top': el.scrolledTo });
      el.stop();
    }
  };
  stickAtTop.unstop = function (el) {
    if (el.stopped()) {
      el.$fixedEl.css({ 'position': '', 'top': '' });
      el.unstop();
    }
  };

  // Extension of sticky object to add behaviours specific to sticking to bottom of window
  var stickAtBottom = new Sticky('.js-stick-at-bottom-when-scrolling');
  // Store bottom of sticky elements while unstuck
  stickAtBottom.getScrolledFrom = function ($el) {
    return $el.offset().top + $el.outerHeight();
  };
  // Store furthest point bottom of sticky element is allowed
  stickAtBottom.getScrollingTo = function (el) {
    var header = $('.js-header:eq(0)');
    if (header.length === 0) {
      return 0;
    }
    return (header.offset().top + header.outerHeight() + 10) + el.height;
  };
  stickAtBottom.scrolledFromInsideWindow = function (scrolledFrom) {
    var windowBottom = this.getWindowPositions().scrollTop + this.getWindowDimensions().height;

    return scrolledFrom < windowBottom;
  };
  stickAtBottom.scrolledToOutsideWindow = function (el, windowHeight) {
    var windowBottom = this.getWindowPositions().scrollTop + this.getWindowDimensions().height;

    return windowBottom < el.scrolledTo;
  };
  stickAtBottom.stick = function (el) {
    if (!el.isStuck()) {
      var $el = el.$fixedEl;

      el.addShim('after');
      // element will be absolutely positioned so cannot rely on parent element for width
      el.$fixedEl.css('width', $el.width() + 'px').addClass(el.stickyClass());
      el.stick();
    }
  };
  stickAtBottom.stop = function (el) {
    if (!el.stopped()) {
      el.$fixedEl.css({
        'position': 'absolute',
        'top': (el.scrolledTo - el.height),
        'bottom': 'auto'
      });
      el.stop();
    }
  };
  stickAtBottom.unstop = function (el) {
    if (el.stopped()) {
      el.$fixedEl.css({
        'position': '',
        'top': '',
        'bottom': ''
      });
      el.unstop();
    }
  };

  GOVUK.stickAtTopWhenScrolling = stickAtTop;
  GOVUK.stickAtBottomWhenScrolling = stickAtBottom;
  global.GOVUK = GOVUK;
})(window);

window.GOVUK.Frontend.initAll();

window.GOVUK.Modules.CookieBanner.clearOldCookies();

if (window.GOVUK.hasConsentFor('analytics')) {
  window.GOVUK.initAnalytics();
}

$(() => $("time.timeago").timeago());

$(() => GOVUK.stickAtTopWhenScrolling.init());
$(() => GOVUK.stickAtBottomWhenScrolling.init());

var showHideContent = new GOVUK.ShowHideContent();
showHideContent.init();

$(() => GOVUK.modules.start());

$(() => $('.error-message').eq(0).parent('label').next('input').trigger('focus'));

$(() => $('.banner-dangerous').eq(0).trigger('focus'));

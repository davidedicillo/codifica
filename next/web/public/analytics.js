/* An empty frame keeps enhanced measurement away from app forms and content.
   Never read parent.location, parent.document, invitation URLs, or account data. */
window.dataLayer = window.dataLayer || [];
function gtag() { window.dataLayer.push(arguments); }
gtag('js', new Date());
gtag('config', 'G-3D57Q2FVD8', {
  page_location: 'https://codifica.app/',
  page_referrer: '',
  page_title: 'Codifica',
  allow_google_signals: false,
  allow_ad_personalization_signals: false,
});
if (location.hostname === 'codifica.app') {
  const tag = document.createElement('script');
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtag/js?id=G-3D57Q2FVD8';
  document.head.appendChild(tag);
}

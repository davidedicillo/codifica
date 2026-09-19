import { post } from './api';

// Once per document load. GA sees only the empty, constant-URL frame.
export function startPageAnalytics() {
  if (location.hostname !== 'codifica.app' || document.getElementById('page-analytics')) return;
  const frame = document.createElement('iframe');
  frame.id = 'page-analytics';
  frame.title = 'Page analytics';
  frame.hidden = true;
  frame.referrerPolicy = 'no-referrer';
  frame.src = '/analytics.html';
  document.body.appendChild(frame);
}

export function trackActiveAccount() {
  // Failure must not interrupt normal app use. Deduplication happens on the server.
  const ping = () => {
    if (document.visibilityState === 'visible') void post('/usage/active', {}).catch(() => {});
  };
  ping();
  document.addEventListener('visibilitychange', ping);
  const timer = window.setInterval(ping, 5 * 60 * 1000);
  return () => {
    window.clearInterval(timer);
    document.removeEventListener('visibilitychange', ping);
  };
}

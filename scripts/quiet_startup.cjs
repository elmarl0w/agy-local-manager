'use strict';

// Suppress ONLY known informational startup messages from the pinned proxy.
// This is loaded into the Node adapter process, not the Antigravity TUI.
// Real warnings (including port conflicts), errors and TUI output pass through.
let proxyStartHidden = false;
const portReady = /^ready \(port \d+\)\r?\n?$/;
const combinedReady = /^Starting proxy\.\.\.\s*ready \(port \d+\)\r?\n?$/;
const proxyStart = /^Starting proxy\.\.\.\s*$/;
const compatibilityNotice = /^\[Warn\] agy [^\r\n]+ has not been tested with free-antigravity-cli\./;

function isNoise(chunk) {
  if (typeof chunk !== 'string') return false;
  if (compatibilityNotice.test(chunk)) return true;
  if (combinedReady.test(chunk)) return true;
  if (proxyStart.test(chunk)) {
    proxyStartHidden = true;
    return true;
  }
  if (proxyStartHidden && portReady.test(chunk)) {
    proxyStartHidden = false;
    return true;
  }
  // Never hide any other message: especially port-conflict and proxy errors.
  return false;
}

for (const stream of [process.stdout, process.stderr]) {
  const write = stream.write.bind(stream);
  stream.write = function (chunk, encoding, callback) {
    if (isNoise(chunk)) {
      const done = typeof encoding === 'function' ? encoding : callback;
      if (typeof done === 'function') process.nextTick(done);
      return true;
    }
    return write(chunk, encoding, callback);
  };
}

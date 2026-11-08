'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { scanKey, scanActiveAccount } = require('../scripts/ciphertalk_key_helper.cjs');
const { privateKey } = crypto.generateKeyPairSync('ed25519');

function scanner(results) {
  return {
    koffi: { decode: pointer => JSON.stringify(pointer) },
    library: { func: signature => {
      if (signature.includes('wkt_challenge')) return nonce => { nonce.fill(1); return 32; };
      if (signature.includes('wkt_free')) return () => {};
      return () => results.shift();
    } },
  };
}

test('empty scan is a compatibility failure rather than an account mismatch', () => {
  for (const result of [null, {}, { db_key: 'a'.repeat(64) }]) {
    const { koffi, library } = scanner([result]);
    const output = scanActiveAccount(koffi, library, privateKey, '/data/wxid_example');
    assert.equal(output.errorCode, 'SCANNER_EMPTY_ACCOUNT');
    assert.equal(output.key, '');
  }
});

test('actual account mismatch never returns another account key', () => {
  const { koffi, library } = scanner([{ wxid: 'wxid_other', db_key: 'a'.repeat(64) }]);
  const output = scanActiveAccount(koffi, library, privateKey, '/data/wxid_example');
  assert.equal(output.errorCode, 'ACCOUNT_MISMATCH');
  assert.equal(output.key, '');
});

test('account directory suffix is accepted without claiming database validation', () => {
  const { koffi, library } = scanner([{ wxid: 'wxid_example', db_key: 'a'.repeat(64) }]);
  const output = scanActiveAccount(koffi, library, privateKey, '/data/wxid_example_123');
  assert.equal(output.key.length, 64);
  assert.equal(output.databaseValidated, false);
});

test('failed account fallback retains contact-db scanner diagnostics', () => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'scanner-test-'));
  try {
    fs.writeFileSync(path.join(root, 'contact.db'), 'test');
    const { koffi, library } = scanner([
      { auth: true, db_ok: true, pids: 5, opened: 5, candidates: 526 }, null,
    ]);
    const output = scanKey(koffi, library, privateKey, root);
    assert.equal(output.errorCode, 'SCANNER_EMPTY_ACCOUNT');
    assert.equal(output.diagnostic.candidateCount, 526);
    assert.equal(output.key, '');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

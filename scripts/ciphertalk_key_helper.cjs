#!/usr/bin/env node
/*
 * Headless adapter for CipherTalk's official wechat_key_tool.dll interface.
 * CipherTalk attribution: https://github.com/ILoveBingLu/CipherTalk
 * The official DLL and matching service source remain under CC-BY-NC-SA-4.0.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

function output(value, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
  process.exitCode = exitCode;
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--') || index + 1 >= argv.length) {
      throw new Error(`参数无效: ${item}`);
    }
    result[item.slice(2)] = argv[index + 1];
    index += 1;
  }
  return result;
}

function loadKoffi(modulePath) {
  if (!modulePath) return require('koffi');
  return require(path.resolve(modulePath));
}

function privateKeyFromOfficialSource(sourcePath) {
  const source = fs.readFileSync(sourcePath, 'utf8');
  const match = source.match(/const obf\s*=\s*['"]([0-9a-fA-F]+)['"]/);
  if (!match) throw new Error('官方服务源码中未找到扫描鉴权材料');
  const obfuscated = Buffer.from(match[1], 'hex');
  const der = Buffer.from(obfuscated.map((value) => value ^ 0x5a));
  return crypto.createPrivateKey({ key: der, format: 'der', type: 'pkcs8' });
}

function signedChallenge(koffi, library, privateKey) {
  const challenge = library.func('int wkt_challenge(uint8_t*, size_t)');
  const nonce = Buffer.alloc(32);
  if (challenge(nonce, nonce.length) !== nonce.length) {
    throw new Error('官方扫描组件未返回有效挑战');
  }
  return crypto.sign(null, nonce, privateKey);
}

function decodeResult(koffi, library, pointer) {
  if (!pointer) return null;
  const free = library.func('void wkt_free(void*)');
  try {
    const text = koffi.decode(pointer, 'char', -1);
    return JSON.parse(String(text || '{}').replace(/\0/g, ''));
  } finally {
    free(pointer);
  }
}

function findContactDb(accountPath) {
  const pending = [accountPath];
  let visited = 0;
  while (pending.length && visited < 500) {
    const current = pending.shift();
    visited += 1;
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isFile() && entry.name.toLowerCase() === 'contact.db') return fullPath;
      if (entry.isDirectory()) pending.push(fullPath);
    }
  }
  return null;
}

function scanKey(koffi, library, privateKey, accountPath) {
  const contactDb = findContactDb(accountPath);
  if (contactDb) {
    const signature = signedChallenge(koffi, library, privateKey);
    const scan = library.func('void* wkt_scan_diag_auth(uint8_t*, size_t, str)');
    const result = decodeResult(koffi, library, scan(signature, signature.length, contactDb));
    const key = typeof result?.key === 'string' ? result.key.trim() : '';
    const diagnostic = result ? {
        authenticated: result.auth !== false,
        databaseOpened: result.db_ok !== false,
        processCount: Number(result.pids) || 0,
        openedProcessCount: Number(result.opened) || 0,
        candidateCount: Number(result.candidates) || 0,
      } : null;
    if (/^[0-9a-fA-F]{64}$/.test(key)) {
      return { key, method: 'contact-db-validated', databaseValidated: true, diagnostic };
    }
    const accountResult = scanActiveAccount(koffi, library, privateKey, accountPath);
    return { ...accountResult, diagnostic };
  }

  return scanActiveAccount(koffi, library, privateKey, accountPath);
}

function scanActiveAccount(koffi, library, privateKey, accountPath) {
  const signature = signedChallenge(koffi, library, privateKey);
  const scan = library.func('void* wkt_scan_account_auth(uint8_t*, size_t)');
  const result = decodeResult(koffi, library, scan(signature, signature.length));
  const key = typeof result?.db_key === 'string' ? result.db_key.trim() : '';
  const expectedWxid = path.basename(path.resolve(accountPath));
  const returnedWxid = String(result?.wxid || '').trim();
  if (!result || !returnedWxid) {
    return {
      key: '', method: 'active-account', databaseValidated: false, diagnostic: null,
      error: '扫描组件未返回有效账号信息；可能不支持当前微信版本，不能据此判断账号不匹配',
      errorCode: 'SCANNER_EMPTY_ACCOUNT',
    };
  }
  const accountMatches = returnedWxid && (
    returnedWxid === expectedWxid || expectedWxid.startsWith(`${returnedWxid}_`)
  );
  if (/^wxid_/i.test(expectedWxid) && !accountMatches) {
    return {
      key: '', method: 'active-account', databaseValidated: false, diagnostic: null,
      error: '扫描到的当前微信账号与已配置数据目录不匹配',
      errorCode: 'ACCOUNT_MISMATCH',
    };
  }
  return { key, method: 'active-account', databaseValidated: false, diagnostic: null };
}

function saveMiyuKey(configPath, key) {
  let config = {};
  try {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  const temporary = `${configPath}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify({ ...config, keyHex: key.toLowerCase() }, null, 2)}\n`, {
    encoding: 'utf8',
    mode: 0o600,
  });
  fs.renameSync(temporary, configPath);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  for (const required of ['dll', 'source', 'account-path']) {
    if (!args[required]) throw new Error(`缺少 --${required}`);
  }
  const koffi = loadKoffi(args['koffi-path']);
  const library = koffi.load(path.resolve(args.dll));
  const privateKey = privateKeyFromOfficialSource(path.resolve(args.source));
  const result = scanKey(koffi, library, privateKey, path.resolve(args['account-path']));
  if (!/^[0-9a-fA-F]{64}$/.test(result.key)) {
    output({ ok: false, error: result.error || '未扫描到可验证的数据库密钥', errorCode: result.errorCode || 'KEY_NOT_FOUND', method: result.method, diagnostic: result.diagnostic }, 1);
    return;
  }
  const configPath = args['config-path'] || path.join(os.homedir(), '.miyu', 'config.json');
  saveMiyuKey(path.resolve(configPath), result.key);
  output({
    ok: true,
    saved: true,
    method: result.method,
    databaseValidated: result.databaseValidated,
    diagnostic: result.diagnostic,
  });
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    output({ ok: false, error: error instanceof Error ? error.message : String(error) }, 1);
  }
}

module.exports = { scanKey, scanActiveAccount };

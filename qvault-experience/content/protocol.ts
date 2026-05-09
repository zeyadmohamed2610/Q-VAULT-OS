// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Protocol Content Data
// Handshake steps, byte sizes, protocol states
// ═══════════════════════════════════════════════════════════════

export const PROTOCOL_STEPS = [
  {
    id: 'hello',
    step: 1,
    label: 'HELLO',
    bytes: 5,
    direction: 'service-to-esp' as const,
    description: 'Service polls for hardware token presence.',
    color: '#00e6ff',
  },
  {
    id: 'ready',
    step: 2,
    label: 'READY',
    bytes: 5,
    direction: 'esp-to-service' as const,
    description: 'Token confirms it is in vault mode and ready for handshake.',
    color: '#00ff88',
  },
  {
    id: 'sync-pubkey',
    step: 3,
    label: 'SYNC + PUBLIC KEY',
    bytes: 1188,
    direction: 'service-to-esp' as const,
    description: 'Service generates ML-KEM-768 keypair and sends 4-byte sync frame + 1184-byte public key.',
    color: '#00e6ff',
  },
  {
    id: 'kem-encapsulate',
    step: 4,
    label: 'KEM ENCAPSULATE',
    bytes: 0,
    direction: 'internal-esp' as const,
    description: 'ESP32 encapsulates a 32-byte shared secret using the public key.',
    color: '#9c27ff',
  },
  {
    id: 'ciphertext-payload',
    step: 5,
    label: 'CIPHERTEXT + PAYLOAD',
    bytes: 1376,
    direction: 'esp-to-service' as const,
    description: 'Token returns: 4B magic + 1088B KEM ciphertext + 12B IV + 16B tag + 256B encrypted vault payload.',
    color: '#9c27ff',
  },
  {
    id: 'decrypt-unlock',
    step: 6,
    label: 'DECRYPT + UNLOCK',
    bytes: 0,
    direction: 'internal-service' as const,
    description: 'Service decapsulates shared secret, decrypts payload, unlocks BitLocker, zeroizes memory.',
    color: '#00ff88',
  },
] as const;

export const HANDSHAKE_BYTE_INVENTORY = {
  magicResponse: 4,
  kemCiphertext: 1088,
  aesGcmIv: 12,
  aesGcmTag: 16,
  encryptedPayload: 256,
  total: 1376,
} as const;

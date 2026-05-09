// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Copy Content
// All text content for the experience, centralized
// ═══════════════════════════════════════════════════════════════

export const COPY = {
  hero: {
    title: 'Q-VAULT',
    subtitle: 'Post-quantum hardware custody for encrypted storage.',
    tagline: 'An ESP32-S3 hardware key, ML-KEM-768 exchange, AES-256-GCM payload protection, and BitLocker integration wrapped in a cinematic secure operating environment.',
  },

  threat: {
    headline: 'HARVEST NOW. DECRYPT LATER.',
    body: 'Encrypted traffic captured today can be broken by quantum computers tomorrow. The breach does not need your password today. It can wait.',
  },

  trustStack: {
    headline: 'TRUST IS NOT A LAYER. IT IS A STACK.',
    body: 'Q-Vault splits trust across possession, cryptography, and local policy. No single compromise collapses the system.',
  },

  protocol: {
    headline: 'THE HANDSHAKE',
    body: 'The token never reveals the vault payload in cleartext over USB. A fresh ML-KEM-768 exchange produces a shared secret, the ESP32 encrypts the vault payload with AES-256-GCM, and the service consumes the decrypted secret locally before wiping memory.',
  },

  zeroKnowledge: {
    headline: 'SECRETS BURN AFTER USE',
    body: 'The secret exists only as long as the unlock requires. Then it burns. No cloud. No logs. No command line exposure.',
  },

  os: {
    headline: 'THE COMMAND SURFACE',
    body: 'Q-Vault OS turns invisible security machinery into an interface operators can understand. Terminal, desktop, app sandbox, kernel monitor, runtime trust scores, quarantine, and hardware status.',
  },

  seal: {
    headline: 'SYSTEM SEALED',
    cta_source: 'VIEW SOURCE',
    cta_demo: 'REQUEST DEMO',
    cta_docs: 'READ DOCUMENTATION',
  },
} as const;

// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Threat Model Content Data
// ═══════════════════════════════════════════════════════════════

export const THREATS = [
  {
    id: 'hndl',
    name: 'Harvest Now, Decrypt Later',
    description: 'Adversary captures encrypted traffic today to break with future quantum computers.',
    mitigation: 'ML-KEM-768 exchange instead of classical public-key exchange.',
    metaphor: 'Frozen captured traffic failing to decrypt under a future quantum beam.',
    severity: 'critical' as const,
  },
  {
    id: 'usb-sniff',
    name: 'USB Sniffing',
    description: 'Malicious USB sniffer captures serial traffic between service and token.',
    mitigation: 'Captured data carries only KEM ciphertext and AES-GCM encrypted payload, not raw password.',
    metaphor: 'Packet stream visible to attacker, payload remains sealed.',
    severity: 'high' as const,
  },
  {
    id: 'stolen-laptop',
    name: 'Stolen Laptop',
    description: 'Laptop stolen from user without the hardware token present.',
    mitigation: 'Drive remains BitLocker-locked. Service detects USB removal and forces lock.',
    metaphor: 'Laptop shell with dark locked drive core.',
    severity: 'high' as const,
  },
  {
    id: 'stolen-key',
    name: 'Stolen Hardware Key',
    description: 'Token stolen without the target laptop.',
    mitigation: 'Token alone cannot unlock without specific laptop BitLocker environment.',
    metaphor: 'Token floating near a sealed machine with no trust route.',
    severity: 'medium' as const,
  },
  {
    id: 'replay',
    name: 'MITM / Replay Attack',
    description: 'Adversary replays captured handshake packets.',
    mitigation: 'Fresh KEM exchange per session. Magic sync frames prevent replay.',
    metaphor: 'Replay packet shatters against freshness gate.',
    severity: 'medium' as const,
  },
  {
    id: 'ram-scrape',
    name: 'RAM Scraping',
    description: 'Memory forensics attempting to extract secrets from volatile RAM.',
    mitigation: 'SecureZeroMemory and mbedtls_platform_zeroize wipe secrets immediately after use.',
    metaphor: 'Secret vapor trail disappears after unlock.',
    severity: 'high' as const,
  },
] as const;

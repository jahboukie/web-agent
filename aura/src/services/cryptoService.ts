/**
 * Cryptographic Service for WebAgent Aura Frontend
 *
 * Handles client-side zero-knowledge encryption, key management,
 * and cryptographic operations for secure data handling.
 */

// Storage keys for encrypted data
const PRIVATE_KEY_STORAGE = "webagent_private_key";
const SIGNING_KEY_STORAGE = "webagent_signing_key";
const SALT_STORAGE = "webagent_salt";

// Types
export interface KeyPair {
  publicKey: string;
  privateKey: CryptoKey;
  signingPublicKey: string;
  signingPrivateKey: CryptoKey;
}

export interface EncryptedData {
  data: string;
  iv: string;
  salt: string;
  algorithm: string;
}

export interface KeyDerivationParams {
  password: string;
  salt: Uint8Array;
  iterations: number;
}

class CryptoService {
  private privateKey: CryptoKey | null = null;
  private signingPrivateKey: CryptoKey | null = null;
  private isInitialized = false;

  constructor() {
    this.initializeWebCrypto();
  }

  private async initializeWebCrypto(): Promise<void> {
    if (!window.crypto || !window.crypto.subtle) {
      throw new Error("Web Crypto API not supported in this browser");
    }
    this.isInitialized = true;
  }

  // Key Generation
  async generateKeyPair(): Promise<KeyPair> {
    if (!this.isInitialized) {
      await this.initializeWebCrypto();
    }

    try {
      // Generate encryption key pair (RSA-OAEP for key exchange, AES-GCM for data)
      const encryptionKeyPair = await window.crypto.subtle.generateKey(
        {
          name: "RSA-OAEP",
          modulusLength: 2048,
          publicExponent: new Uint8Array([1, 0, 1]),
          hash: "SHA-256",
        },
        true, // extractable
        ["encrypt", "decrypt"],
      );

      // Generate signing key pair (ECDSA)
      const signingKeyPair = await window.crypto.subtle.generateKey(
        {
          name: "ECDSA",
          namedCurve: "P-256",
        },
        true, // extractable
        ["sign", "verify"],
      );

      // Export public keys
      const publicKey = await this.exportPublicKey(encryptionKeyPair.publicKey);
      const signingPublicKey = await this.exportPublicKey(
        signingKeyPair.publicKey,
      );

      return {
        publicKey,
        privateKey: encryptionKeyPair.privateKey,
        signingPublicKey,
        signingPrivateKey: signingKeyPair.privateKey,
      };
    } catch (error) {
      throw new Error(`Key generation failed: ${error}`);
    }
  }

  // Key Management
  async storePrivateKeys(
    privateKey: CryptoKey,
    signingPrivateKey: CryptoKey,
  ): Promise<void> {
    try {
      // Export keys for storage
      const privateKeyData = await window.crypto.subtle.exportKey(
        "pkcs8",
        privateKey,
      );
      const signingKeyData = await window.crypto.subtle.exportKey(
        "pkcs8",
        signingPrivateKey,
      );

      // Convert to base64 for storage
      const privateKeyB64 = this.arrayBufferToBase64(privateKeyData);
      const signingKeyB64 = this.arrayBufferToBase64(signingKeyData);

      // Store in localStorage (in production, consider IndexedDB for better security)
      localStorage.setItem(PRIVATE_KEY_STORAGE, privateKeyB64);
      localStorage.setItem(SIGNING_KEY_STORAGE, signingKeyB64);

      // Keep in memory for current session
      this.privateKey = privateKey;
      this.signingPrivateKey = signingPrivateKey;
    } catch (error) {
      throw new Error(`Failed to store private keys: ${error}`);
    }
  }

  async loadPrivateKeys(): Promise<boolean> {
    try {
      const privateKeyB64 = localStorage.getItem(PRIVATE_KEY_STORAGE);
      const signingKeyB64 = localStorage.getItem(SIGNING_KEY_STORAGE);

      if (!privateKeyB64 || !signingKeyB64) {
        return false;
      }

      // Convert from base64
      const privateKeyData = this.base64ToArrayBuffer(privateKeyB64);
      const signingKeyData = this.base64ToArrayBuffer(signingKeyB64);

      // Import keys
      this.privateKey = await window.crypto.subtle.importKey(
        "pkcs8",
        privateKeyData,
        {
          name: "RSA-OAEP",
          hash: "SHA-256",
        },
        false,
        ["decrypt"],
      );

      this.signingPrivateKey = await window.crypto.subtle.importKey(
        "pkcs8",
        signingKeyData,
        {
          name: "ECDSA",
          namedCurve: "P-256",
        },
        false,
        ["sign"],
      );

      return true;
    } catch (error) {
      console.error("Failed to load private keys:", error);
      return false;
    }
  }

  clearKeys(): void {
    localStorage.removeItem(PRIVATE_KEY_STORAGE);
    localStorage.removeItem(SIGNING_KEY_STORAGE);
    localStorage.removeItem(SALT_STORAGE);
    this.privateKey = null;
    this.signingPrivateKey = null;
  }

  // Encryption/Decryption
  async encryptData(data: string, password?: string): Promise<EncryptedData> {
    try {
      // Generate random salt and IV
      const salt = window.crypto.getRandomValues(new Uint8Array(16));
      const iv = window.crypto.getRandomValues(new Uint8Array(12));

      // Derive key from password or use stored key
      let key: CryptoKey;
      if (password) {
        key = await this.deriveKeyFromPassword(password, salt);
      } else {
        // Use AES key derived from user's master key
        key = await this.generateAESKey();
      }

      // Encrypt data
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);

      const encryptedBuffer = await window.crypto.subtle.encrypt(
        {
          name: "AES-GCM",
          iv: iv,
        },
        key,
        dataBuffer,
      );

      return {
        data: this.arrayBufferToBase64(encryptedBuffer),
        iv: this.arrayBufferToBase64(iv),
        salt: this.arrayBufferToBase64(salt),
        algorithm: "AES-GCM",
      };
    } catch (error) {
      throw new Error(`Encryption failed: ${error}`);
    }
  }

  async decryptData(
    encryptedData: EncryptedData,
    password?: string,
  ): Promise<string> {
    try {
      // Convert from base64
      const dataBuffer = this.base64ToArrayBuffer(encryptedData.data);
      const iv = this.base64ToArrayBuffer(encryptedData.iv);
      const salt = this.base64ToArrayBuffer(encryptedData.salt);

      // Derive key
      let key: CryptoKey;
      if (password) {
        key = await this.deriveKeyFromPassword(password, new Uint8Array(salt));
      } else {
        key = await this.generateAESKey();
      }

      // Decrypt data
      const decryptedBuffer = await window.crypto.subtle.decrypt(
        {
          name: "AES-GCM",
          iv: iv,
        },
        key,
        dataBuffer,
      );

      const decoder = new TextDecoder();
      return decoder.decode(decryptedBuffer);
    } catch (error) {
      throw new Error(`Decryption failed: ${error}`);
    }
  }

  // Digital Signatures
  async signData(data: string): Promise<string> {
    if (!this.signingPrivateKey) {
      await this.loadPrivateKeys();
      if (!this.signingPrivateKey) {
        throw new Error("No signing key available");
      }
    }

    try {
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);

      const signature = await window.crypto.subtle.sign(
        {
          name: "ECDSA",
          hash: "SHA-256",
        },
        this.signingPrivateKey,
        dataBuffer,
      );

      return this.arrayBufferToBase64(signature);
    } catch (error) {
      throw new Error(`Signing failed: ${error}`);
    }
  }

  async verifySignature(
    data: string,
    signature: string,
    publicKey: string,
  ): Promise<boolean> {
    try {
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);
      const signatureBuffer = this.base64ToArrayBuffer(signature);

      // Import public key
      const publicKeyBuffer = this.base64ToArrayBuffer(publicKey);
      const cryptoPublicKey = await window.crypto.subtle.importKey(
        "spki",
        publicKeyBuffer,
        {
          name: "ECDSA",
          namedCurve: "P-256",
        },
        false,
        ["verify"],
      );

      return await window.crypto.subtle.verify(
        {
          name: "ECDSA",
          hash: "SHA-256",
        },
        cryptoPublicKey,
        signatureBuffer,
        dataBuffer,
      );
    } catch (error) {
      console.error("Signature verification failed:", error);
      return false;
    }
  }

  // Hashing
  async hash(data: string, algorithm: string = "SHA-256"): Promise<string> {
    try {
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);
      const hashBuffer = await window.crypto.subtle.digest(
        algorithm,
        dataBuffer,
      );
      return this.arrayBufferToBase64(hashBuffer);
    } catch (error) {
      throw new Error(`Hashing failed: ${error}`);
    }
  }

  // Utility Methods
  private async deriveKeyFromPassword(
    password: string,
    salt: Uint8Array,
  ): Promise<CryptoKey> {
    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(password);

    // Import password as key material
    const keyMaterial = await window.crypto.subtle.importKey(
      "raw",
      passwordBuffer,
      "PBKDF2",
      false,
      ["deriveKey"],
    );

    // Derive AES key
    return await window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: salt,
        iterations: 100000,
        hash: "SHA-256",
      },
      keyMaterial,
      {
        name: "AES-GCM",
        length: 256,
      },
      false,
      ["encrypt", "decrypt"],
    );
  }

  private async generateAESKey(): Promise<CryptoKey> {
    return await window.crypto.subtle.generateKey(
      {
        name: "AES-GCM",
        length: 256,
      },
      false,
      ["encrypt", "decrypt"],
    );
  }

  private async exportPublicKey(publicKey: CryptoKey): Promise<string> {
    const exported = await window.crypto.subtle.exportKey("spki", publicKey);
    return this.arrayBufferToBase64(exported);
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  // Generate secure random values
  generateSecureRandom(length: number = 32): string {
    const array = new Uint8Array(length);
    window.crypto.getRandomValues(array);
    return this.arrayBufferToBase64(array.buffer);
  }

  // Check if crypto is available
  isSupported(): boolean {
    return !!(window.crypto && window.crypto.subtle);
  }
}

// Export singleton instance
export const cryptoService = new CryptoService();
export default cryptoService;

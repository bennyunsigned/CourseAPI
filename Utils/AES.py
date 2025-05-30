from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import base64

class AESCipher:
    def __init__(self, secret_key: str = "kjhdsvjfjsdgfjgjhgsdfooiejjd", username: str = "unsignedbenny", password: str = "abcd@1234"):
        """
        Initialize the AES cipher with a fixed salt for consistent encryption and decryption.
        """
        self.salt = b'\x00' * 16  # Use a fixed salt for testing (replace with secure storage in production)
        combined_key = f"{secret_key}{username}{password}"
        self.key = PBKDF2(combined_key, self.salt, dkLen=32, count=100000)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt the plaintext using AES-GCM encryption.
        :param plaintext: The text to encrypt.
        :return: The base64-encoded ciphertext.
        """
        cipher = AES.new(self.key, AES.MODE_GCM)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        return base64.b64encode(nonce + tag + ciphertext).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt the ciphertext using AES-GCM decryption.
        :param ciphertext: The base64-encoded ciphertext to decrypt.
        :return: The decrypted plaintext.
        """
        raw_data = base64.b64decode(ciphertext)
        nonce = raw_data[:16]
        tag = raw_data[16:32]
        encrypted_data = raw_data[32:]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(encrypted_data, tag)
        return plaintext.decode('utf-8')

if __name__ == "__main__":
    # Example usage
    aes_cipher = AESCipher()  # Using default values for secret_key, username, and password

    plaintext = "This is a secret message."
    print(f"Original: {plaintext}")

    encrypted = aes_cipher.encrypt(plaintext)
    print(f"Encrypted: {encrypted}")

    decrypted = aes_cipher.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
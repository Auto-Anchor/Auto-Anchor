from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding #AES padding
from cryptography.hazmat.backends import default_backend
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding # Rename RSA padding
from cryptography.hazmat.primitives import serialization, hashes
import json


class Encryption():

    def generate_rsa_keys(self, password):
        """
        Generate RSA key pair with password-protected private key.
        
        Args:
            password (str): Password to encrypt the private key
        
        Returns:
            tuple: (password-encrypted private key PEM, public key PEM)
        """
        # Convert password to bytes
        password_bytes = password.encode()
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537, 
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Save Private Key with password encryption
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password_bytes)
        )
        
        # Save Public Key 
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return pem_private, pem_public
    

    # Encrypt AES key using RSA Public Key
    def encrypt_aes_key_using_rsa(self,aes_key, public_key_pem):
        public_key = serialization.load_pem_public_key(public_key_pem)
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf = asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted_aes_key).decode()


    def encrypt_aes(self,data, key):
        """Encrypt data using AES-256-CBC."""
        iv = os.urandom(16)  # Generate a random IV
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data to match AES block size (16 bytes)
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode()) + padder.finalize()
        
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return IV + encrypted data, encoded in base64
        return base64.b64encode(iv + encrypted).decode()
    
    
    # Save Encrypted Data to File
    def save_to_file(self,filename, encrypted_aes_key, encrypted_private, encrypted_public, rsa_private_key):
        """Save encrypted data and RSA private key to a JSON file."""
        data = {
            "encrypted_aes_key": encrypted_aes_key,
            "encrypted_private_key": encrypted_private,
            "encrypted_public_key": encrypted_public,
            # "rsa_private_key": rsa_private_key.decode()  # Save RSA Private Key (for later decryption)
            "rsa_private_key": base64.b64encode(rsa_private_key).decode('utf-8')
        }
        with open(filename, "w") as file:
            json.dump(data, file)



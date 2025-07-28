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

class Decryption():
        
    # Decrypt AES Key Using RSA Private Key 
    def decrypt_aes_key_rsa(self, encrypted_aes_key, private_key_pem, password="AUTOANCHORHASH"):    # supports password-based decryption 

        """
        Decrypt AES Key Using RSA Private Key with password protection
        
        Args:
            encrypted_aes_key (str): Base64 encoded encrypted AES key
            private_key_pem (bytes): Password-encrypted private key PEM
            password (str): Password to decrypt the private key
        """

        # Convert password to bytes
        password_bytes = password.encode()
        
        # Load private key with password
        private_key = serialization.load_pem_private_key(
            private_key_pem, 
            password=password_bytes
        )
        
        # Decrypt AES key
        decrypted_aes_key = private_key.decrypt(
            base64.b64decode(encrypted_aes_key),
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_aes_key

    # Load Encrypted Data from File
    def load_from_file(self,filename):
        with open(filename, "r") as file:
            return json.load(file)

    # def load_encrypted_bundle(self, filename):
    #     """Loads the JSON bundle containing the encrypted data."""
    #     with open(filename, "r") as file:
    #         return json.load(file)

    def decrypt_aes(self,encrypted_data, key):
        """Decrypt data using AES-256-CBC."""
        encrypted_data = base64.b64decode(encrypted_data)
        iv = encrypted_data[:16]  # Extract IV
        encrypted = encrypted_data[16:]
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
        
        # Remove padding
        unpadder = sym_padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode()
    

    def _generate_credentials_xml(self,work_dir,private_key_path):
        
        ssh_data = self._github_ssh_key()
        
        if not ssh_data:
            print("Failed to retrieve SCM data.")
            return  

        try:
            # Parse the existing credentials.xml file
            work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed
            
            folder_name = os.path.join(work_dir, "shell_files")
        
            os.makedirs(folder_name, exist_ok=True)

            file_path = os.path.join(work_dir, 'shell_files/credentials.xml')

            with open(file_path, "w") as f:
                f.write(xml_creds)
            
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find the privateKey element
            private_key_element = root.find(
                ".//privateKeySource/privateKey"
            )

            if private_key_element is None:
                print("privateKey element not found in the XML.")
                return

            # Insert the private key
            private_key_element.text = ssh_data.strip()

            # Write changes back to the file
            tree.write(file_path, encoding="UTF-8", xml_declaration=True)
            print(f"Private key successfully added to {file_path}.")

        except Exception as e:
            print(f"An error occurred while updating credentials.xml: {e}")


    def write_keys_to_files(self,decrypted_private, decrypted_public):
        """
        Write decrypted private and public keys to files in the user's home directory (~/.ssh/).
        
        Args:
            decrypted_private (str): Decrypted private key content
            decrypted_public (str): Decrypted public key content
        """
        # Expand the home directory path
        ssh_dir = os.path.expanduser("~/.ssh")
        
        # Ensure the directory exists
        os.makedirs(ssh_dir, exist_ok=True)
        
        # Define file paths
        private_key_path = os.path.join(ssh_dir, "id_ed25519")
        public_key_path = os.path.join(ssh_dir, "id_ed25519.pub")
        
        # Write private key with restricted permissions
        with open(private_key_path, "w") as f:
            f.write(decrypted_private)
        os.chmod(private_key_path, 0o600)  # Read/write for owner only
        
        # Write public key
        with open(public_key_path, "w") as f:
            f.write(decrypted_public)
        os.chmod(public_key_path, 0o644)  # Read/write for owner, read for others
        
        print(f"Private key written to: {private_key_path}")
        print(f"Public key written to: {public_key_path}")


if __name__ == "__main__":

    decrypt=Decryption()

    # Load Encrypted Data
    data = decrypt.load_from_file("encrypted_keys.json")

    # Decrypt AES Key Using RSA Private Key
    # rsa_private_key_pem = data["rsa_private_key"].encode()
    rsa_private_key_pem = base64.b64decode(data["rsa_private_key"])
    decrypted_aes_key = decrypt.decrypt_aes_key_rsa(data["encrypted_aes_key"], rsa_private_key_pem)

    # Decrypt Private and Public Keys Using Decrypted AES Key
    decrypted_private = decrypt.decrypt_aes(data["encrypted_private_key"], decrypted_aes_key)
    decrypted_public = decrypt.decrypt_aes(data["encrypted_public_key"], decrypted_aes_key)



    decrypt.write_keys_to_files(decrypted_private, decrypted_public)


    print(f"Decrypted Private Key: {decrypted_private}")
    print(f"Decrypted Public Key: {decrypted_public}")
import os
import xml.etree.ElementTree as ET
import argparse

def update_credentials_xml(credentials_path,ssh_key_path=None):
    """

    Update the credentials.xml file with a new SSH private key.
    
    :param credentials_path: Path to the credentials.xml file.
    :param ssh_key_path: Path to the SSH private key file. 
                          If None, searches in ~/.ssh/ directory.
    :return: Boolean indicating success of update
    
    """
    if ssh_key_path==None:
        ssh_key_path = '~/.ssh/'
    # # Default path for SSH keys
    # if not ssh_key_path:
    ssh_dir = os.path.expanduser(ssh_key_path)
    
    print(ssh_dir)

    # Find the first private key in ~/.ssh/
    private_keys = [
        os.path.join(ssh_dir, f) 
        for f in os.listdir(ssh_dir) 
        if f.startswith('id_') and not f.endswith('.pub')
    ]
    
    if not private_keys:
        print("No private SSH key found in ~/.ssh/")
        return False
    
    ssh_key_path = private_keys[0]
    
    # Read the SSH private key
    try:
        with open(ssh_key_path, 'r') as key_file:
            private_key = key_file.read().strip()
    except IOError as e:
        print(f"Error reading SSH key: {e}")
        return False
    
    try:
        # Parse the XML
        tree = ET.parse(credentials_path)
        root = tree.getroot()
        
        # Find the privateKey element
        private_key_elem = root.find(".//privateKey")
        
        if private_key_elem is not None:
            # Replace the private key content
            private_key_elem.text = private_key
        else:
            print("Could not find privateKey element in XML")
            return False
        
        # Write back to the file
        tree.write(credentials_path, encoding='utf-8', xml_declaration=True)
        
        print(f"Successfully updated credentials.xml with key from {ssh_key_path}")
        return True
    
    except ET.ParseError as e:
        print(f"XML Parsing error: {e}")
        return False
    except IOError as e:
        print(f"File write error: {e}")
        return False

# Example usage
if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Update credentials.xml with a new SSH private key.")
    parser.add_argument("credentials_path", help="Path to the credentials.xml file.")
    parser.add_argument("--ssh_key_path", help="Path to the SSH private key. If not provided, the script will search in ~/.ssh/")
    
    args = parser.parse_args()
    
    # Call the function with the provided arguments
    update_credentials_xml(args.credentials_path, args.ssh_key_path)
    # update_credentials_xml(args.credentials_path)

"""

To run the script with both credentials.xml and ssh_key paths specified:
python script.py /path/to/credentials.xml --ssh_key_path /path/to/ssh_key


To run the script where it finds the SSH key in ~/.ssh/ and just updates credentials.xml:
python script.py /path/to/credentials.xml

"""
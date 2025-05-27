from cryptography.fernet import Fernet

# Generate a new Fernet key
fernet_key = Fernet.generate_key()

# Print the key in a format that can be directly used in docker-compose
print(f"Generated Fernet Key: {fernet_key.decode()}") 
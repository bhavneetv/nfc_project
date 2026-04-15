from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


private_key = ec.generate_private_key(ec.SECP256R1())
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)

import base64

public_b64 = base64.urlsafe_b64encode(public_pem).decode("utf-8").rstrip("=")
private_num = private_key.private_numbers().private_value.to_bytes(32, "big")
private_b64 = base64.urlsafe_b64encode(private_num).decode("utf-8").rstrip("=")

print("VAPID_PUBLIC_KEY=" + public_b64)
print("VAPID_PRIVATE_KEY=" + private_b64)
print("Save these in backend/.env")

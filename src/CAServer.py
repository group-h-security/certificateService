from pathlib import Path

from flask import Flask
from flask import jsonify
from flask import request
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec # The two key algorithims we allow
from cryptography.exceptions import InvalidSignature # for catching bad signatures
from cryptography.hazmat.primitives.asymmetric import padding # Needed for verifying RSA keys
from cryptography.hazmat.primitives import hashes # Hashing algo that CSRs use
# For building certs
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import CertificateBuilder
from datetime import datetime, timedelta

from jinja2.lexer import TOKEN_DOT

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
INTERMEDIATE_KEY = PROJECT_ROOT / "CertsAndKeys" / "PrivateKeys" / "intermediate.key"
INTERMEDIATE_CERT = PROJECT_ROOT / "CertsAndKeys" / "Certificates" / "intermediate.crt"

app = Flask(__name__)

@app.route("/")
def home():
	return jsonify({
		"status": "okay",
		"message": "flask is running"

	})

# The Main Script

@app.route("/sign", methods=["POST"])
def sign():
    # First, we have to make sure a csr file actually came in with the post request
    if "csr" not in request.files:
        return ("Missing file field 'csr'\n", 400, {"Content-Type": "text/plain"})

    # After enuring its present, we get the raw bytes from the file.
    raw = request.files["csr"].read()

    # CSRs are typically encoded in PEM so we try that first. If that fails, default to DER
    try:
        csr = x509.load_pem_x509_csr(raw)
    except ValueError:
        csr = x509.load_der_x509_csr(raw)

    # Get the Subject + Common Name + Public Key from CSR
    subject_str = csr.subject.rfc4514_string()
    cn_attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    cn = cn_attrs[0].value if cn_attrs else None
    rqPublicKey = csr.public_key()

    # === Key validation policy ===

    # RSA: require >= 2048 bits
    if isinstance(rqPublicKey, rsa.RSAPublicKey):
        key_size = rqPublicKey.key_size
        if key_size < 2048:
            return (f"Rejected: RSA key too small ({key_size} bits). Require >= 2048.\n",
                    400, {"Content-Type": "text/plain"})
        algo_desc = f"RSA-{key_size}"

    # EC: Only allow curves considered safe
    elif isinstance(rqPublicKey, ec.EllipticCurvePublicKey):
        curve_name = rqPublicKey.curve.name  # e.g. 'secp256r1'
        allowed_curves = {"secp256r1", "secp384r1", "secp521r1"}
        if curve_name not in allowed_curves:
            return (f"Rejected: EC curve '{curve_name}' not allowed. "
                    f"Allowed: {', '.join(sorted(allowed_curves))}.\n",
                    400, {"Content-Type": "text/plain"})
        algo_desc = f"EC-{curve_name}"

    # Reject anything not RSA or EC
    else:
        return (f"Rejected: Unsupported public key type: {type(rqPublicKey).__name__}\n",
                400, {"Content-Type": "text/plain"})
    # === end key validation ===

    # === private key validation ===

    # Ensuring that the public key in the csr can correctly hash with the private key its signed with
    try:
        if isinstance(rqPublicKey, rsa.RSAPublicKey):
            rqPublicKey.verify(
                csr.signature,
                csr.tbs_certrequest_bytes,
                padding.PKCS1v15(),
                csr.signature_hash_algorithm,
            )

        elif isinstance(rqPublicKey, ec.EllipticCurvePublicKey):
            rqPublicKey.verify(
                csr.signature,
                csr.tbs_certrequest_bytes,
                ec.ECDSA(csr.signature_hash_algorithm),
            )

    except InvalidSignature:
        return ("Rejected: CSR signature invalid (does not match public key).\n",
                           400, {"Content-Type": "text/plain"})

   # === end private key validation ===

    # Logging it all to the server
    print("\n===== CSR RECEIVED =====")
    try:
        print(raw.decode("utf-8"))
    except UnicodeDecodeError:
        print(f"[binary CSR received: {len(raw)} bytes]")
    print(f"Subject: {subject_str}")
    print(f"Common Name (CN): {cn}")
    print(f"Key: {algo_desc}")
    print("===== END CSR =====\n", flush=True)

    clientCert = printCert(csr)

    with open(INTERMEDIATE_CERT, "r") as f:
        interPem = f.read()
    chainPem = clientCert + "\n" + interPem


    # Default response for now
    return (chainPem, 200, {"Content-Type": "application/x-pem-file"})



##################################
# TODO
# Make the constraints config for client certs we build
def printCert(csr):
    # opening the private key and the cert
    with open(INTERMEDIATE_KEY, "rb") as f: # rb = read mode - binary
        keyData = f.read()
    try:
        caKey = serialization.load_pem_private_key(keyData, password=None)
    except ValueError:
        caKey = serialization.load_der_private_key(keyData, password=None)

    with open(INTERMEDIATE_CERT, "rb") as f:
        certData = f.read()
    try:
        caCert = x509.load_pem_x509_certificate(certData)
    except ValueError:
        caCert = x509.load_der_x509_certificate(certData)

    # Build the client cert with the csr data
    builder = (
        CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(caCert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=90))
    )

    # copy csr extensions if present
    for ext in csr.extensions:
        builder = builder.add_extension(ext.value, ext.critical)

    new_cert = builder.sign(
        private_key = caKey,
        algorithm=hashes.SHA256()
    )

    cert_pem = new_cert.public_bytes(serialization.Encoding.PEM).decode()
    return cert_pem

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)


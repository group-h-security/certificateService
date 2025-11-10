# Generating the private key for the root
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out root.key

# Generating private key for the intermediate cert
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out intermediate.key
# Generate the self-signed cert for the Root CA
openssl req -new -x509 -days 3650 -sha256 -key root.key -out rootCert.crt -config root.cnf -extensions v3_ca

# Generate the CSR for the intermediate cert - signed with the intermediate private key for authentication
openssl req -new -key intermediate.key -out intermediate.csr -config intermediate.cnf

# Generate the Intermediate cert using the above CSR and the CARoot key, issuing it with the rootCert.crt
openssl x509 -req -in intermediate.csr -CA rootCert.crt -CAkey root.key -CAcreateserial -out intermediate.crt -days 1825 -sha256 -extfile Intermediate.cnf -extensions v3_req

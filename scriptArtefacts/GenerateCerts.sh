# Generate the self-signed cert for the Root CA
openssl req -new -x509 -days 3650 -sha256 -key root.key -out rootCert.crt -config root.cnf -extensions v3_ca

# Generate the CSR for the intermediate cert - signed with the intermediate private key for authentication
openssl req -new -key intermediate.key -out intermediate.csr -config intermediate.cnf

# Generate the Intermediate cert using the above CSR and the CARoot key, issuing it with the rootCert.crt
openssl x509 -req -in intermediate.csr -CA rootCert.crt -CAkey root.key -CAcreateserial -out intermediate.crt -days 1825 -sha256 -extfile Intermediate.cnf -extensions v3_req

# Generate the CSR for the flask server's cert
openssl req -new \
  -key PrivateKeys/flask-server.key \
  -out Certificates/flask-server.csr \
  -config Certificates/temp.cnf

  # Generate the flask server cert with the intermediate cert
openssl x509 -req \
  -in Certificates/flask-server.csr \
  -CA Certificates/intermediate.crt \
  -CAkey PrivateKeys/intermediate.key \
  -CAcreateserial \
  -out Certificates/flask-server.crt \
  -days 365 \
  -extensions req_ext \
  -extfile Certificates/temp.cnf

# Manually build the chain for the flask server because writing the code to print one cert like this is pointless
cat Certificates/flask-server.crt Certificates/intermediate.crt > Certificates/flask-server-chain.pem

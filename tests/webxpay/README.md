# WebXPay Test Fixtures

`test_private.pem` and `test_public.pem` are **test-only** RSA key pairs.

They are committed to the repository solely to enable offline unit testing of the
WebXPay encryption and signature verification logic without real credentials.

**Never use these keys in staging or production.**
**Never commit real WebXPay keys to the repository.**

# Firebase release SHA setup

Release signing is **not** configured in this workspace (`keystore.properties` absent).
Only **debug** SHA-1 / SHA-256 are registered in Firebase.

## After you create the upload keystore

1. Generate fingerprints:

```bash
keytool -list -v -keystore upload-keystore.jks -alias upload
```

2. Add to Firebase Android app `1:1055213565369:android:8335551a7cdbacb7abb268`:

```bash
firebase use poisker-84437
firebase apps:android:sha:create 1:1055213565369:android:8335551a7cdbacb7abb268 <SHA1_OR_SHA256>
firebase apps:android:sha:list 1:1055213565369:android:8335551a7cdbacb7abb268
```

3. After Play App Signing is enabled, copy **App signing** SHA-256 from Play Console → App integrity and add it the same way.

4. Update `https://poisker.ru/.well-known/assetlinks.json` with the **Play App Signing** SHA-256 (the cert on users’ devices), plus upload/debug as needed.

Do **not** invent fingerprints.

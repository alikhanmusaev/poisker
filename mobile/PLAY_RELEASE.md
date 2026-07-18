# Play release checklist (Flutter)

1. Create upload keystore (do **not** commit):
   ```bash
   keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
2. Add `android/key.properties` (gitignored):
   ```
   storePassword=...
   keyPassword=...
   keyAlias=upload
   storeFile=/absolute/path/upload-keystore.jks
   ```
3. Wire signing in `android/app/build.gradle.kts` (release → upload keystore).
4. `flutter build appbundle`
5. Upload AAB to Play Console → App Signing.
6. Copy **App signing** SHA-1/SHA-256 into Firebase Android app + `assetlinks.json` if using App Links.
7. Store privacy policy URL: `https://poisker.ru/privacy`

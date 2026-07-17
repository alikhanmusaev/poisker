# Google Play checklist — Поискер (`ru.poisker.app`)

## Сборка

- [ ] `./gradlew clean assembleDebug` успешен
- [ ] `./gradlew test` успешен
- [ ] `./gradlew lint` без блокирующих ошибок
- [ ] `keystore.properties` заполнен реальным upload keystore
- [ ] `./gradlew :app:bundleRelease` создаёт AAB
- [ ] `versionCode` / `versionName` обновлены перед каждой публикацией

## Store listing

- [ ] Название: Поискер
- [ ] Краткое описание (до 80 символов)
- [ ] Полное описание
- [ ] Иконка 512×512
- [ ] Feature graphic 1024×500
- [ ] Скриншоты телефона (мобильный сайт в WebView)
- [ ] Категория: Shopping / Lifestyle (уточнить)
- [ ] Контактный email разработчика
- [ ] Ссылка на политику: https://poisker.ru/privacy
- [ ] Ссылка на условия: https://poisker.ru/terms

## Data safety

Заполнить по [PRIVACY_AND_DATA_SAFETY.md](PRIVACY_AND_DATA_SAFETY.md):

- [ ] Регистрация / аккаунт
- [ ] Пользовательский контент (объявления, фото, сообщения)
- [ ] Нет рекламы SDK
- [ ] Нет сторонней аналитики в приложении
- [ ] Данные обрабатываются на poisker.ru

## App Links

- [ ] `assetlinks.json` доступен по HTTPS
- [ ] В JSON добавлен SHA-256 **Play App Signing** сертификата
- [ ] Проверка: `adb shell pm verify-app-links --re-verify ru.poisker.app`
- [ ] Открытие `https://poisker.ru/...` из Chrome предлагает приложение

## Безопасность / политики

- [ ] Release: `usesCleartextTraffic=false`
- [ ] Нет SSL bypass
- [ ] Нет `addJavascriptInterface`
- [ ] WebView debugging только в debug
- [ ] CAMERA только runtime
- [ ] Нет `CALL_PHONE`, location, contacts, `QUERY_ALL_PACKAGES`

## Контент / модерация

- [ ] В описании указать, что это доска объявлений (UGC)
- [ ] Указать модерацию объявлений на стороне сервиса
- [ ] Возрастной рейтинг по анкете Play (UGC)

## Перед отправкой

- [ ] Проверить логин Django в WebView
- [ ] Создать объявление с фото
- [ ] tel: открывает dialer
- [ ] Внешняя ссылка открывается в браузере
- [ ] Back возвращает по истории WebView
- [ ] Offline экран и Retry
- [ ] Поворот экрана не сбрасывает форму/сессию

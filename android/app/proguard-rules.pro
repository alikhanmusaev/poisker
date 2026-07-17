# Add project specific ProGuard rules here.
-keepclassmembers class * extends android.webkit.WebViewClient { *; }
-keepclassmembers class * extends android.webkit.WebChromeClient { *; }
-dontwarn android.webkit.**

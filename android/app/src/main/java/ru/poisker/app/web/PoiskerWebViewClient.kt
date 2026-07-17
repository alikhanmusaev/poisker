package ru.poisker.app.web

import android.graphics.Bitmap
import android.net.http.SslError
import android.webkit.HttpAuthHandler
import android.webkit.SslErrorHandler
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import androidx.webkit.WebResourceErrorCompat
import androidx.webkit.WebViewClientCompat
import ru.poisker.app.util.UrlRules

class PoiskerWebViewClient(
    private val onPageStarted: (url: String?) -> Unit,
    private val onPageFinished: (url: String?) -> Unit,
    private val onMainFrameError: (PageError) -> Unit,
    private val onExternalUrl: (url: String) -> Boolean,
) : WebViewClientCompat() {

    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        val url = request.url?.toString().orEmpty()
        if (UrlRules.shouldHandleInWebView(url)) {
            return false
        }
        return onExternalUrl(url)
    }

    @Deprecated("Deprecated in Java")
    override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
        if (UrlRules.shouldHandleInWebView(url)) {
            return false
        }
        return onExternalUrl(url.orEmpty())
    }

    override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
        super.onPageStarted(view, url, favicon)
        onPageStarted(url)
    }

    override fun onPageFinished(view: WebView?, url: String?) {
        super.onPageFinished(view, url)
        onPageFinished(url)
    }

    override fun onReceivedError(
        view: WebView,
        request: WebResourceRequest,
        error: WebResourceErrorCompat,
    ) {
        if (!request.isForMainFrame) return
        val description = error.description?.toString().orEmpty()
        val code = error.errorCode
        val pageError = when (code) {
            ERROR_HOST_LOOKUP,
            ERROR_CONNECT,
            ERROR_TIMEOUT,
            ERROR_IO,
            ERROR_PROXY_AUTHENTICATION,
            -> PageError.Network(description.ifBlank { "Network error ($code)" })
            ERROR_FAILED_SSL_HANDSHAKE -> PageError.Ssl(description.ifBlank { "SSL error" })
            else -> PageError.Unknown(description.ifBlank { "Load error ($code)" })
        }
        onMainFrameError(pageError)
    }

    @Deprecated("Deprecated in Java")
    override fun onReceivedError(
        view: WebView?,
        errorCode: Int,
        description: String?,
        failingUrl: String?,
    ) {
        val pageError = when (errorCode) {
            ERROR_HOST_LOOKUP,
            ERROR_CONNECT,
            ERROR_TIMEOUT,
            ERROR_IO,
            -> PageError.Network(description.orEmpty())
            ERROR_FAILED_SSL_HANDSHAKE -> PageError.Ssl(description.orEmpty())
            else -> PageError.Unknown(description.orEmpty())
        }
        onMainFrameError(pageError)
    }

    override fun onReceivedHttpError(
        view: WebView,
        request: WebResourceRequest,
        errorResponse: WebResourceResponse,
    ) {
        if (!request.isForMainFrame) return
        val code = errorResponse.statusCode
        if (code == 404 || code >= 500) {
            onMainFrameError(PageError.Http(code))
        }
    }

    override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {
        handler?.cancel()
        onMainFrameError(PageError.Ssl(error?.toString().orEmpty().ifBlank { "SSL certificate error" }))
    }

    override fun onReceivedHttpAuthRequest(
        view: WebView?,
        handler: HttpAuthHandler?,
        host: String?,
        realm: String?,
    ) {
        handler?.cancel()
    }
}

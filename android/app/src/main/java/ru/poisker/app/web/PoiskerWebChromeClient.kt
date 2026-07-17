package ru.poisker.app.web

import android.net.Uri
import android.webkit.ConsoleMessage
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView

class PoiskerWebChromeClient(
    private val onProgressChanged: (Int) -> Unit,
    private val fileChooserHandler: FileChooserHandler,
) : WebChromeClient() {

    override fun onProgressChanged(view: WebView?, newProgress: Int) {
        onProgressChanged(newProgress)
    }

    override fun onShowFileChooser(
        webView: WebView?,
        filePathCallback: ValueCallback<Array<Uri>>?,
        fileChooserParams: FileChooserParams?,
    ): Boolean {
        if (filePathCallback == null || fileChooserParams == null) {
            return false
        }
        return fileChooserHandler.showChooser(filePathCallback, fileChooserParams)
    }

    override fun onPermissionRequest(request: PermissionRequest?) {
        // Do not grant camera/mic WebRTC permissions automatically.
        request?.deny()
    }

    override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
        // Swallow console in production shell; avoid noisy logging.
        return true
    }
}

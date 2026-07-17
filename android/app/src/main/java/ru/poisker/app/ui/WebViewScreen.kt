package ru.poisker.app.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.FrameLayout
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.launch
import ru.poisker.app.BuildConfig
import ru.poisker.app.R
import ru.poisker.app.network.NetworkMonitor
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.web.DownloadHandler
import ru.poisker.app.web.ExternalLinkHandler
import ru.poisker.app.web.FileChooserHandler
import ru.poisker.app.web.PoiskerWebChromeClient
import ru.poisker.app.web.PoiskerWebViewClient
import ru.poisker.app.web.WebViewStateHolder
import ru.poisker.app.web.WebViewUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WebViewScreen(
    startUrl: String = BuildConfig.START_URL,
    pendingNavigationUrl: String? = null,
    onNavigationConsumed: () -> Unit = {},
    onSessionLikelyReady: () -> Unit = {},
    stateHolder: WebViewStateHolder,
    networkMonitor: NetworkMonitor,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }

    var uiState by remember {
        mutableStateOf(
            WebViewUiState(
                isOfflineBeforeLoad = !networkMonitor.isOnline,
                isLoading = networkMonitor.isOnline,
            ),
        )
    }
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var pendingCameraGrant by remember { mutableStateOf<(() -> Unit)?>(null) }
    val fileChooserHandlerHolder = remember { arrayOfNulls<FileChooserHandler>(1) }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        val action = pendingCameraGrant
        pendingCameraGrant = null
        if (granted) {
            action?.invoke()
        } else {
            fileChooserHandlerHolder[0]?.cancel()
        }
    }

    val fileChooserHandler = remember {
        FileChooserHandler(
            activityContext = { context },
            requestCameraPermission = { onGranted ->
                pendingCameraGrant = onGranted
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            },
        ).also { fileChooserHandlerHolder[0] = it }
    }

    // Wire Activity Result launchers once.
    fileChooserHandler.openDocuments = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri != null) fileChooserHandler.onReceiveValue(arrayOf(uri))
        else fileChooserHandler.cancel()
    }
    fileChooserHandler.openMultipleDocuments = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        if (uris.isNotEmpty()) fileChooserHandler.onReceiveValue(uris.toTypedArray())
        else fileChooserHandler.cancel()
    }
    fileChooserHandler.takePicture = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicture(),
    ) { success ->
        fileChooserHandler.onCameraResult(success)
    }
    fileChooserHandler.pickVisualMedia = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia(),
    ) { uri ->
        if (uri != null) fileChooserHandler.onReceiveValue(arrayOf(uri))
        else fileChooserHandler.cancel()
    }
    fileChooserHandler.pickMultipleVisualMedia = rememberLauncherForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(),
    ) { uris ->
        if (uris.isNotEmpty()) fileChooserHandler.onReceiveValue(uris.toTypedArray())
        else fileChooserHandler.cancel()
    }

    // Track connectivity for banner (do not wipe already loaded page).
    LaunchedEffect(networkMonitor) {
        networkMonitor.connectivityFlow().collect { online ->
            uiState = uiState.copy(
                showOfflineBanner = !online && uiState.pageError == null && !uiState.isOfflineBeforeLoad,
                isOfflineBeforeLoad = if (online && uiState.isOfflineBeforeLoad) false else uiState.isOfflineBeforeLoad,
            )
            if (online && uiState.isOfflineBeforeLoad) {
                uiState = uiState.copy(isOfflineBeforeLoad = false, isLoading = true)
                webViewRef?.loadUrl(startUrl)
            }
            if (!online) {
                scope.launch {
                    snackbarHostState.showSnackbar(context.getString(R.string.offline_banner))
                }
            }
        }
    }

    LaunchedEffect(pendingNavigationUrl, webViewRef) {
        val target = pendingNavigationUrl?.takeIf { it.isNotBlank() } ?: return@LaunchedEffect
        val webView = webViewRef ?: return@LaunchedEffect
        uiState = uiState.copy(pageError = null, isOfflineBeforeLoad = false, isLoading = true)
        webView.loadUrl(target)
        onNavigationConsumed()
    }

    LaunchedEffect(uiState.currentUrl, uiState.isLoading) {
        if (!uiState.isLoading && uiState.currentUrl.isNotBlank() && uiState.pageError == null) {
            onSessionLikelyReady()
        }
    }

    val currentUi by rememberUpdatedState(uiState)

    BackHandler(enabled = true) {
        val webView = webViewRef
        when {
            currentUi.pageError != null -> {
                uiState = uiState.copy(pageError = null)
            }
            webView != null && webView.canGoBack() -> webView.goBack()
            else -> {
                // Finish activity
                (context as? android.app.Activity)?.finish()
            }
        }
    }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_PAUSE -> {
                    CookieManager.getInstance().flush()
                    webViewRef?.let { view ->
                        val bundle = Bundle()
                        view.saveState(bundle)
                        stateHolder.save(bundle)
                        stateHolder.lastLoadedUrl = view.url
                    }
                }
                Lifecycle.Event.ON_RESUME -> {
                    CookieManager.getInstance().flush()
                }
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            webViewRef?.let { view ->
                val bundle = Bundle()
                view.saveState(bundle)
                stateHolder.save(bundle)
                stateHolder.lastLoadedUrl = view.url
            }
        }
    }

    Box(modifier = modifier.fillMaxSize()) {
        when {
            uiState.isOfflineBeforeLoad -> {
                OfflineScreen(
                    onRetry = {
                        if (networkMonitor.isOnline) {
                            uiState = uiState.copy(isOfflineBeforeLoad = false, isLoading = true, pageError = null)
                            webViewRef?.loadUrl(startUrl) ?: run {
                                // WebView not yet created — flag clears so AndroidView mounts and loads.
                            }
                        } else {
                            scope.launch {
                                snackbarHostState.showSnackbar(context.getString(R.string.still_offline))
                            }
                        }
                    },
                )
            }
            uiState.pageError != null -> {
                ErrorScreen(
                    error = uiState.pageError!!,
                    onRetry = {
                        uiState = uiState.copy(pageError = null, isLoading = true)
                        webViewRef?.reload() ?: webViewRef?.loadUrl(startUrl)
                    },
                    onOpenInBrowser = {
                        val url = webViewRef?.url ?: startUrl
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    },
                )
            }
            else -> {
                PullToRefreshBox(
                    isRefreshing = uiState.isRefreshing,
                    onRefresh = {
                        val webView = webViewRef
                        if (webView != null && webView.scrollY == 0) {
                            uiState = uiState.copy(isRefreshing = true)
                            webView.reload()
                        }
                    },
                    modifier = Modifier.fillMaxSize(),
                ) {
                    Column(modifier = Modifier.fillMaxSize()) {
                        if (uiState.isLoading || uiState.progress in 1..99) {
                            LinearProgressIndicator(
                                progress = { (uiState.progress.coerceIn(0, 100)) / 100f },
                                modifier = Modifier.fillMaxWidth(),
                                color = PoiskerColors.Primary,
                                trackColor = PoiskerColors.PrimarySoft,
                            )
                        }
                        PoiskerWebView(
                            startUrl = startUrl,
                            stateHolder = stateHolder,
                            fileChooserHandler = fileChooserHandler,
                            onWebViewCreated = { webViewRef = it },
                            onUiChange = { patch -> uiState = patch(uiState) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }

        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(16.dp),
        ) { data ->
            Snackbar(
                action = {
                    TextButton(onClick = {
                        data.dismiss()
                        if (networkMonitor.isOnline) {
                            uiState = uiState.copy(pageError = null, isOfflineBeforeLoad = false, isLoading = true)
                            webViewRef?.reload()
                        }
                    }) {
                        Text(stringResource(R.string.action_retry))
                    }
                },
            ) {
                Text(data.visuals.message)
            }
        }

        if (uiState.showOfflineBanner && uiState.pageError == null && !uiState.isOfflineBeforeLoad) {
            Text(
                text = stringResource(R.string.offline_banner),
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .padding(8.dp),
                color = PoiskerColors.Primary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun PoiskerWebView(
    startUrl: String,
    stateHolder: WebViewStateHolder,
    fileChooserHandler: FileChooserHandler,
    onWebViewCreated: (WebView) -> Unit,
    onUiChange: ((WebViewUiState) -> WebViewUiState) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { ctx ->
            WebView(ctx).apply {
                layoutParams = FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                )
                configurePoiskerWebView(this)

                webViewClient = PoiskerWebViewClient(
                    onPageStarted = { url ->
                        onUiChange {
                            it.copy(
                                isLoading = true,
                                currentUrl = url.orEmpty(),
                                pageError = null,
                            )
                        }
                    },
                    onPageFinished = { url ->
                        CookieManager.getInstance().flush()
                        onUiChange {
                            it.copy(
                                isLoading = false,
                                isRefreshing = false,
                                currentUrl = url.orEmpty(),
                                canGoBack = canGoBack(),
                                progress = 100,
                            )
                        }
                    },
                    onMainFrameError = { error ->
                        onUiChange {
                            it.copy(
                                isLoading = false,
                                isRefreshing = false,
                                pageError = error,
                            )
                        }
                    },
                    onExternalUrl = { url ->
                        ExternalLinkHandler.open(context, url)
                    },
                )

                webChromeClient = PoiskerWebChromeClient(
                    onProgressChanged = { progress ->
                        onUiChange {
                            it.copy(
                                progress = progress,
                                isLoading = progress < 100,
                            )
                        }
                    },
                    fileChooserHandler = fileChooserHandler,
                )

                setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
                    DownloadHandler.enqueue(context, url, userAgent, contentDisposition, mimeType)
                }

                val restored = stateHolder.consumeSavedState()
                if (restored != null) {
                    restoreState(restored)
                    if (url.isNullOrBlank()) {
                        loadUrl(stateHolder.lastLoadedUrl ?: startUrl)
                    }
                } else {
                    loadUrl(startUrl)
                }
                onWebViewCreated(this)
            }
        },
        update = { view ->
            onWebViewCreated(view)
        },
    )
}

@SuppressLint("SetJavaScriptEnabled")
fun configurePoiskerWebView(webView: WebView) {
    CookieManager.getInstance().apply {
        setAcceptCookie(true)
        setAcceptThirdPartyCookies(webView, true)
    }

    with(webView.settings) {
        javaScriptEnabled = true
        domStorageEnabled = true
        loadsImagesAutomatically = true
        mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        allowFileAccess = false
        allowContentAccess = true
        setSupportMultipleWindows(false)
        javaScriptCanOpenWindowsAutomatically = false
        mediaPlaybackRequiresUserGesture = true
        builtInZoomControls = false
        displayZoomControls = false
        useWideViewPort = true
        loadWithOverviewMode = true
        setSupportZoom(false)
        cacheMode = WebSettings.LOAD_DEFAULT
        userAgentString = "$userAgentString ${BuildConfig.APP_USER_AGENT_SUFFIX}"
    }

    webView.isVerticalScrollBarEnabled = true
    webView.isHorizontalScrollBarEnabled = false
    WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
}

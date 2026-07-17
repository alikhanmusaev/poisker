package ru.poisker.app.web

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File

/**
 * Handles WebChromeClient.onShowFileChooser with Activity Result API.
 * Camera is used only when HTML requests capture.
 */
class FileChooserHandler(
    private val activityContext: () -> Context,
    private val requestCameraPermission: (onGranted: () -> Unit) -> Unit,
) {
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var cameraImageUri: Uri? = null

    lateinit var openDocuments: ActivityResultLauncher<Array<String>>
    lateinit var openMultipleDocuments: ActivityResultLauncher<Array<String>>
    lateinit var takePicture: ActivityResultLauncher<Uri>
    lateinit var pickVisualMedia: ActivityResultLauncher<PickVisualMediaRequest>
    lateinit var pickMultipleVisualMedia: ActivityResultLauncher<PickVisualMediaRequest>

    fun onReceiveValue(uris: Array<Uri>?) {
        filePathCallback?.onReceiveValue(uris)
        filePathCallback = null
        cameraImageUri = null
    }

    fun cancel() {
        filePathCallback?.onReceiveValue(null)
        filePathCallback = null
        cameraImageUri = null
    }

    fun showChooser(
        filePathCallback: ValueCallback<Array<Uri>>,
        fileChooserParams: WebChromeClient.FileChooserParams,
    ): Boolean {
        this.filePathCallback?.onReceiveValue(null)
        this.filePathCallback = filePathCallback

        val acceptTypes = fileChooserParams.acceptTypes
            ?.filter { it.isNotBlank() }
            ?.toTypedArray()
            ?.ifEmpty { arrayOf("*/*") }
            ?: arrayOf("*/*")
        val allowMultiple = fileChooserParams.mode == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE
        val wantsImage = acceptTypes.any {
            it == "*/*" || it.startsWith("image/", ignoreCase = true)
        }
        val captureHint = fileChooserParams.isCaptureEnabled

        if (captureHint && wantsImage) {
            launchCameraOrFallback(acceptTypes, allowMultiple)
            return true
        }

        launchPicker(
            acceptTypes = acceptTypes,
            allowMultiple = allowMultiple,
            prefersImages = wantsImage && acceptTypes.all {
                it == "*/*" || it.startsWith("image/", ignoreCase = true)
            },
        )
        return true
    }

    private fun launchCameraOrFallback(acceptTypes: Array<String>, allowMultiple: Boolean) {
        val context = activityContext()
        val hasCamera = context.packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)
        if (!hasCamera) {
            launchPicker(acceptTypes, allowMultiple, prefersImages = true)
            return
        }
        val permissionGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        if (!permissionGranted) {
            requestCameraPermission {
                startCameraCapture(acceptTypes, allowMultiple)
            }
            return
        }
        startCameraCapture(acceptTypes, allowMultiple)
    }

    private fun startCameraCapture(acceptTypes: Array<String>, allowMultiple: Boolean) {
        try {
            val context = activityContext()
            val photoFile = File.createTempFile(
                "poisker_capture_${System.currentTimeMillis()}",
                ".jpg",
                context.cacheDir,
            )
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                photoFile,
            )
            cameraImageUri = uri
            takePicture.launch(uri)
        } catch (_: Exception) {
            launchPicker(acceptTypes, allowMultiple, prefersImages = true)
        }
    }

    private fun launchPicker(acceptTypes: Array<String>, allowMultiple: Boolean, prefersImages: Boolean) {
        try {
            if (prefersImages && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val request = PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                if (allowMultiple) {
                    pickMultipleVisualMedia.launch(request)
                } else {
                    pickVisualMedia.launch(request)
                }
                return
            }
            if (allowMultiple) {
                openMultipleDocuments.launch(acceptTypes)
            } else {
                openDocuments.launch(acceptTypes)
            }
        } catch (_: Exception) {
            cancel()
        }
    }

    fun onCameraResult(success: Boolean) {
        val uri = cameraImageUri
        if (success && uri != null) {
            onReceiveValue(arrayOf(uri))
        } else {
            cancel()
        }
    }
}

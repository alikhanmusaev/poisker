package ru.poisker.app.push

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

class PushTokenSyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val manager = PushTokenManager(applicationContext)
        val token = inputData.getString(KEY_TOKEN)
            ?: runCatching { FirebaseMessaging.getInstance().token.await() }.getOrNull()
            ?: return Result.retry()
        return if (manager.registerCurrentToken(token)) Result.success() else Result.retry()
    }

    companion object {
        private const val UNIQUE = "poisker_push_token_sync"
        const val KEY_TOKEN = "token"

        fun enqueue(context: Context, token: String? = null) {
            val request = OneTimeWorkRequestBuilder<PushTokenSyncWorker>()
                .setInputData(workDataOf(KEY_TOKEN to token))
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE,
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }
    }
}

class PushUnregisterWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val ok = PushTokenManager(applicationContext).unregisterCurrentDevice()
        return if (ok) Result.success() else Result.retry()
    }

    companion object {
        fun enqueue(context: Context) {
            val request = OneTimeWorkRequestBuilder<PushUnregisterWorker>().build()
            WorkManager.getInstance(context).enqueue(request)
        }
    }
}

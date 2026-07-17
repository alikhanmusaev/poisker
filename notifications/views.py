from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from api.permissions import IsNotBlocked
from notifications.models import PushDevice
from notifications.services import deactivate_device, get_or_create_preferences, register_device


class PushDeviceRegisterView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        device_id = (request.data.get("device_id") or "").strip()
        platform = (request.data.get("platform") or PushDevice.PLATFORM_ANDROID).strip()
        app_version = (request.data.get("app_version") or "")[:32]
        try:
            app_build = int(request.data.get("app_build") or 0)
        except (TypeError, ValueError):
            return Response(
                {"code": "invalid", "message": "app_build must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not token or not device_id:
            return Response(
                {"code": "invalid", "message": "token and device_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(token) > 512 or len(device_id) > 64:
            return Response(
                {"code": "invalid", "message": "token or device_id too long"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            device = register_device(
                user=request.user,
                token=token,
                device_id=device_id,
                platform=platform,
                app_version=app_version,
                app_build=app_build,
            )
        except ValueError as exc:
            return Response(
                {"code": "invalid", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "id": device.pk,
                "device_id": device.device_id,
                "platform": device.platform,
                "active": device.active,
            },
            status=status.HTTP_201_CREATED,
        )


class PushDeviceCurrentView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def delete(self, request):
        device_id = (
            (request.query_params.get("device_id") or "").strip()
            or (request.data.get("device_id") or "").strip()
            or (request.headers.get("X-Device-Id") or "").strip()
        )
        if not device_id:
            return Response(
                {"code": "invalid", "message": "device_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deactivated = deactivate_device(user=request.user, device_id=device_id)
        return Response({"deactivated": deactivated}, status=status.HTTP_200_OK)


class NotificationPreferenceView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        pref = get_or_create_preferences(request.user)
        return Response(_pref_payload(pref))

    def patch(self, request):
        pref = get_or_create_preferences(request.user)
        for field in (
            "messages_enabled",
            "listings_enabled",
            "system_enabled",
            "marketing_enabled",
        ):
            if field in request.data:
                setattr(pref, field, bool(request.data.get(field)))
        # Marketing requires explicit True; never coerce from missing.
        pref.save()
        return Response(_pref_payload(pref))


def _pref_payload(pref) -> dict:
    return {
        "messages_enabled": pref.messages_enabled,
        "listings_enabled": pref.listings_enabled,
        "system_enabled": pref.system_enabled,
        "marketing_enabled": pref.marketing_enabled,
    }

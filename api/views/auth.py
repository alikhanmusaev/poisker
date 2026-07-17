from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from api.permissions import IsNotBlocked
from api.serializers.auth import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer
from core.http import get_client_ip
from core.ratelimit import hit_rate_limit

User = get_user_model()


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-register:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            return Response(
                {"code": "rate_limited", "message": "Слишком много попыток. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.consent_ip = ip if ip != "unknown" else None
        user.save(update_fields=["consent_ip"])

        try:
            from accounts.services.email import send_verification_email

            send_verification_email(request, user)
        except Exception:
            pass

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "Аккаунт создан. Подтвердите email для входа.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-login:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            return Response(
                {"code": "rate_limited", "message": "Слишком много попыток. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _tokens_for_user(user)
        return Response({"tokens": tokens, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"code": "validation_error", "message": "Укажите refresh token", "fields": {"refresh": ["Обязательное поле"]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            return Response(
                {"code": "validation_error", "message": "Недействительный refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

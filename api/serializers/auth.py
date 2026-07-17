from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import User
from core.phone import ensure_phone_available


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "phone",
            "email_verified",
            "rating_avg",
            "rating_count",
            "created_at",
        )
        read_only_fields = fields


class PublicSellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "display_name", "rating_avg", "rating_count")


class RegisterSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=80)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    accept_terms = serializers.BooleanField()
    accept_pdn = serializers.BooleanField()

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        try:
            return ensure_phone_available(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("Примите условия использования")
        return value

    def validate_accept_pdn(self, value):
        if not value:
            raise serializers.ValidationError("Дайте согласие на обработку персональных данных")
        return value

    def create(self, validated_data):
        from django.conf import settings
        from django.utils import timezone

        validated_data.pop("accept_terms")
        validated_data.pop("accept_pdn")
        email = validated_data["email"].strip().lower()
        user = User.objects.create_user(
            email=email,
            password=validated_data["password"],
            display_name=validated_data["display_name"].strip(),
            phone=validated_data["phone"],
        )
        now = timezone.now()
        user.email_verified = False
        user.terms_accepted_at = now
        user.pdn_consent_at = now
        user.pdn_consent_version = getattr(settings, "PDN_CONSENT_VERSION", "")
        user.save(
            update_fields=[
                "email_verified",
                "terms_accepted_at",
                "pdn_consent_at",
                "pdn_consent_version",
            ]
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs["email"].strip().lower()
        user = authenticate(request, email=email, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Неверный email или пароль.")
        if user.is_blocked:
            raise serializers.ValidationError("Аккаунт заблокирован.")
        if not user.email_verified and not user.is_staff:
            raise serializers.ValidationError(
                "Подтвердите email. Проверьте почту или запросите письмо повторно."
            )
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=80, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate_phone(self, value):
        user = self.context["request"].user
        try:
            return ensure_phone_available(value, exclude_user_id=user.id)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

    def update(self, instance, validated_data):
        if "display_name" in validated_data:
            instance.display_name = validated_data["display_name"].strip()
        if "phone" in validated_data:
            instance.phone = validated_data["phone"]
        instance.save()
        from listings.services.posts import sync_user_post_phones

        sync_user_post_phones(instance)
        return instance

from rest_framework import serializers
from .models import CustomUser

ALLOWED_ROLES = {"student", "admin"}

class UserListSerializer(serializers.ModelSerializer):
    role = serializers.CharField()

    class Meta:
        model = CustomUser
        fields = ["id", "email", "name", "role", "status", "is_staff"]

    def validate_role(self, value):
        v = (value or "").strip().lower()
        if v not in ALLOWED_ROLES:
            raise serializers.ValidationError("Role must be 'student' or 'admin'.")
        return v

    def update(self, instance, validated_data):
        # Only role is editable via this serializer
        new_role = validated_data.get("role", None)
        if new_role:
            # Keep DB value consistent with your current model’s casing:
            # write with Title-case to match your defaults (no migration needed).
            instance.role = "Admin" if new_role == "admin" else "Student"
        instance.save(update_fields=["role"])
        return instance

from rest_framework import serializers
from users.models import User


class UserSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    position_display = serializers.CharField(source='get_position_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'department', 'department_display',
            'position', 'position_display', 'salary', 'hire_date',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value


class UserCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'department', 'position', 'salary', 'hire_date'
        ]

    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        user.sync_to_core_service()
        return user


class SyncToCoreSerializer(serializers.Serializer):

    schema_id = serializers.IntegerField(
        default=1,
        help_text="ID схемы в Core Service"
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="ID пользователей для синхронизации"
    )

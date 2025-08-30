from rest_framework import serializers
from tables.models import TableSchema, TableData


class TableSchemaSerializer(serializers.ModelSerializer):

    class Meta:
        model = TableSchema
        fields = [
            'id', 'name', 'description', 'fields_config',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_fields_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("fields_config должен быть объектом")

        if 'fields' not in value:
            raise serializers.ValidationError("Отсутствует ключ 'fields'")

        if not isinstance(value['fields'], list):
            raise serializers.ValidationError("'fields' должен быть массивом")

        for field in value['fields']:
            if not isinstance(field, dict):
                raise serializers.ValidationError("Каждое поле должно быть объектом")

            required_keys = ['name', 'type']
            for key in required_keys:
                if key not in field:
                    raise serializers.ValidationError(f"Поле должно содержать '{key}'")

        return value


class TableDataSerializer(serializers.ModelSerializer):

    schema_name = serializers.CharField(source='schema.name', read_only=True)

    class Meta:
        model = TableData
        fields = [
            'id', 'schema', 'schema_name', 'data',
            'source_service', 'source_id', 'created_at', 'updated_at'
        ]


class PopulateTableSerializer(serializers.Serializer):

    source_service = serializers.CharField(max_length=50)
    data = serializers.ListField(
        child=serializers.DictField(),
        help_text="Массив объектов с данными"
    )

    def validate_data(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("data должен быть массивом")

        if len(value) == 0:
            raise serializers.ValidationError("data не может быть пустым")

        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Каждый элемент data должен быть объектом")

        return value

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from tables.models import TableSchema, TableData
from .serializers import (
    TableSchemaSerializer,
    TableDataSerializer,
    PopulateTableSerializer
)


class TableSchemaViewSet(viewsets.ModelViewSet):

    queryset = TableSchema.objects.filter(is_active=True)
    serializer_class = TableSchemaSerializer

    def get_queryset(self):
        queryset = TableSchema.objects.filter(is_active=True)

        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        schema = self.get_object()
        data_entries = TableData.objects.filter(schema=schema).order_by('-created_at')

        page = self.paginate_queryset(data_entries)
        if page is not None:
            serializer = TableDataSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TableDataSerializer(data_entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def populate(self, request, pk=None):
        schema = self.get_object()

        populate_serializer = PopulateTableSerializer(data=request.data)
        if not populate_serializer.is_valid():
            return Response(
                populate_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = populate_serializer.validated_data
        data_list = validated_data['data']
        source_service = validated_data['source_service']

        created_entries = []

        try:
            with transaction.atomic():
                for entry in data_list:
                    table_data = TableData.objects.create(
                        schema=schema,
                        data=entry,
                        source_service=source_service,
                        source_id=entry.get('id', '')
                    )
                    created_entries.append(table_data)

            serializer = TableDataSerializer(created_entries, many=True)
            return Response({
                'message': f'Успешно создано {len(created_entries)} записей',
                'count': len(created_entries),
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'Ошибка при создании записей: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'])
    def clear_data(self, request, pk=None):
        schema = self.get_object()
        deleted_count = TableData.objects.filter(schema=schema).count()
        TableData.objects.filter(schema=schema).delete()

        return Response({
            'message': f'Удалено {deleted_count} записей из схемы "{schema.name}"'
        })


class TableDataViewSet(viewsets.ModelViewSet):

    queryset = TableData.objects.all()
    serializer_class = TableDataSerializer

    def get_queryset(self):
        queryset = TableData.objects.select_related('schema').order_by('-created_at')

        schema_id = self.request.query_params.get('schema', None)
        if schema_id:
            queryset = queryset.filter(schema_id=schema_id)

        source_service = self.request.query_params.get('source_service', None)
        if source_service:
            queryset = queryset.filter(source_service=source_service)

        return queryset

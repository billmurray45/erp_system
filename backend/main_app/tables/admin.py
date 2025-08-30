from django.contrib import admin
from .models import TableSchema, TableData


@admin.register(TableSchema)
class TableSchemaAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TableData)
class TableDataAdmin(admin.ModelAdmin):
    list_display = ['schema', 'source_service', 'source_id', 'created_at']
    list_filter = ['source_service', 'created_at']
    search_fields = ['schema__name', 'source_service']
    readonly_fields = ['created_at', 'updated_at']

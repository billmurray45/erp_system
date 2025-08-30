from django.db import models
from django.contrib.auth.models import User
import json


class TableSchema(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название схемы"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    fields_config = models.JSONField(
        verbose_name="Конфигурация полей",
        help_text="JSON с описанием полей таблицы"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
    )

    class Meta:
        verbose_name = "Схема таблицы"
        verbose_name_plural = "Схемы таблиц"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_field_names(self):
        """Получить список названий полей"""
        return [field['name'] for field in self.fields_config.get('fields', [])]


class TableData(models.Model):
    schema = models.ForeignKey(
        TableSchema,
        on_delete=models.CASCADE,
        related_name='data_entries',
        verbose_name="Схема"
    )
    data = models.JSONField(
        verbose_name="Данные записи"
    )
    source_service = models.CharField(
        max_length=50,
        verbose_name="Сервис-источник"
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID в сервисе-источнике"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Данные таблицы"
        verbose_name_plural = "Данные таблиц"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.schema.name} - {self.source_service}"

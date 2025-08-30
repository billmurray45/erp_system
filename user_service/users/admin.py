from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'department', 'position', 'hire_date', 'is_active']
    list_filter = ['department', 'position', 'is_active', 'hire_date']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    readonly_fields = ['created_at', 'updated_at']

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = 'ФИО'

from django.db import models
from django.core.validators import EmailValidator
import requests
from django.conf import settings


class User(models.Model):

    DEPARTMENT_CHOICES = [
        ('IT', 'IT отдел'),
        ('HR', 'Отдел кадров'),
        ('MARKETING', 'Маркетинг'),
        ('SALES', 'Продажи'),
        ('FINANCE', 'Финансы'),
        ('LEGAL', 'Юридический отдел'),
    ]

    POSITION_CHOICES = [
        ('JUNIOR_DEV', 'Junior разработчик'),
        ('SENIOR_DEV', 'Senior разработчик'),
        ('TEAM_LEAD', 'Тимлид'),
        ('MANAGER', 'Менеджер'),
        ('DIRECTOR', 'Директор'),
        ('SPECIALIST', 'Специалист'),
        ('ANALYST', 'Аналитик'),
    ]

    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Логин"
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        unique=True,
        verbose_name="Email"
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Фамилия"
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        verbose_name="Отдел"
    )
    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        verbose_name="Должность"
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Зарплата"
    )
    hire_date = models.DateField(
        verbose_name="Дата приема"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
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
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_table_data(self):
        return {
            "id": str(self.id),
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "department": self.get_department_display(),
            "position": self.get_position_display(),
            "salary": float(self.salary) if self.salary else None,
            "hire_date": self.hire_date.isoformat(),
            "is_active": self.is_active
        }

    def sync_to_core_service(self):
        try:
            data = self.to_table_data()
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/schemas/1/populate/",
                json={
                    "source_service": "user_service",
                    "data": [data]
                },
                timeout=5
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Ошибка синхронизации с Core Service: {e}")
            return False

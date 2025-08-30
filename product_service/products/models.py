from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import requests
from django.conf import settings


class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название категории"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name="Родительская категория"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
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
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Supplier(models.Model):

    name = models.CharField(
        max_length=200,
        verbose_name="Название поставщика"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Контактное лицо"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Телефон"
    )
    address = models.TextField(
        blank=True,
        verbose_name="Адрес"
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
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):

    STATUS_CHOICES = [
        ('ACTIVE', 'Активен'),
        ('INACTIVE', 'Неактивен'),
        ('DISCONTINUED', 'Снят с производства'),
        ('OUT_OF_STOCK', 'Нет в наличии'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name="Название товара"
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Артикул (SKU)"
    )
    barcode = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        verbose_name="Штрих-код"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Поставщик"
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Себестоимость"
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Цена продажи"
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Цена со скидкой"
    )

    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Количество на складе"
    )
    min_stock_level = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Минимальный уровень запаса"
    )
    max_stock_level = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name="Максимальный уровень запаса"
    )

    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Вес (кг)"
    )
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        help_text="Формат: длина x ширина x высота",
        verbose_name="Габариты"
    )

    # Статус и даты
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name="Статус"
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Рекомендуемый товар"
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
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def profit_margin(self):
        if self.cost_price and self.selling_price:
            return (self.selling_price - self.cost_price) / self.selling_price * 100
        return 0

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.selling_price

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level

    @property
    def stock_status(self):
        if self.stock_quantity == 0:
            return "Нет в наличии"
        elif self.is_low_stock:
            return "Заканчивается"
        else:
            return "В наличии"

    def to_table_data(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "sku": self.sku,
            "barcode": self.barcode or "",
            "category": self.category.get_full_path(),
            "supplier": self.supplier.name if self.supplier else "",
            "cost_price": float(self.cost_price),
            "selling_price": float(self.selling_price),
            "current_price": float(self.current_price),
            "profit_margin": round(self.profit_margin, 2),
            "stock_quantity": self.stock_quantity,
            "stock_status": self.stock_status,
            "min_stock_level": self.min_stock_level,
            "weight": float(self.weight) if self.weight else None,
            "dimensions": self.dimensions,
            "status": self.get_status_display(),
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat(),
        }

    def sync_to_core_service(self, schema_id=2):
        try:
            data = self.to_table_data()
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/schemas/{schema_id}/populate/",
                json={
                    "source_service": "product_service",
                    "data": [data]
                },
                timeout=5
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Ошибка синхронизации с Core Service: {e}")
            return False


class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Товар"
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        verbose_name="Изображение"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Альтернативный текст"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Основное изображение"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата загрузки"
    )

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Изображение для {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)

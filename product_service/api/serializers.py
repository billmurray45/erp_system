from rest_framework import serializers
from products.models import Category, Supplier, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):

    full_path = serializers.CharField(source='get_full_path', read_only=True)
    products_count = serializers.IntegerField(
        source='products.count',
        read_only=True
    )
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'full_path',
            'products_count', 'subcategories', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_subcategories(self, obj):
        if self.context.get('include_subcategories', False):
            subcategories = obj.subcategories.filter(is_active=True)
            return CategorySerializer(subcategories, many=True, context={'include_subcategories': False}).data
        return []


class SupplierSerializer(serializers.ModelSerializer):

    products_count = serializers.IntegerField(
        source='products.count',
        read_only=True
    )

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone',
            'address', 'products_count', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        if value:
            supplier_id = self.instance.id if self.instance else None
            if Supplier.objects.filter(email=value).exclude(id=supplier_id).exists():
                raise serializers.ValidationError("Поставщик с таким email уже существует")
        return value


class ProductImageSerializer(serializers.ModelSerializer):

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'image_url', 'alt_text', 'is_primary', 'created_at']
        read_only_fields = ['created_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductListSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    stock_status = serializers.CharField(read_only=True)
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name', 'supplier_name',
            'current_price', 'stock_quantity', 'stock_status',
            'status', 'status_display', 'is_featured',
            'primary_image_url', 'created_at'
        ]

    def get_primary_image_url(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        return None


class ProductSerializer(serializers.ModelSerializer):

    # Связанные объекты
    category_name = serializers.CharField(source='category.get_full_path', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    profit_margin = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    stock_status = serializers.CharField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'description',
            'category', 'category_name', 'supplier', 'supplier_name',
            'cost_price', 'selling_price', 'discount_price',
            'current_price', 'profit_margin',
            'stock_quantity', 'min_stock_level', 'max_stock_level',
            'stock_status', 'is_low_stock',
            'weight', 'dimensions',
            'status', 'status_display', 'is_featured',
            'images', 'primary_image',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image, context=self.context).data
        first_image = obj.images.first()
        if first_image:
            return ProductImageSerializer(first_image, context=self.context).data
        return None

    def validate_sku(self, value):
        product_id = self.instance.id if self.instance else None
        if Product.objects.filter(sku=value).exclude(id=product_id).exists():
            raise serializers.ValidationError("Товар с таким SKU уже существует")
        return value

    def validate_barcode(self, value):
        if value:
            product_id = self.instance.id if self.instance else None
            if Product.objects.filter(barcode=value).exclude(id=product_id).exists():
                raise serializers.ValidationError("Товар с таким штрих-кодом уже существует")
        return value

    def validate(self, attrs):
        cost_price = attrs.get('cost_price', getattr(self.instance, 'cost_price', None))
        selling_price = attrs.get('selling_price', getattr(self.instance, 'selling_price', None))

        if cost_price and selling_price and selling_price <= cost_price:
            raise serializers.ValidationError({
                'selling_price': 'Цена продажи должна быть больше себестоимости'
            })

        discount_price = attrs.get('discount_price')
        if discount_price and selling_price and discount_price >= selling_price:
            raise serializers.ValidationError({
                'discount_price': 'Скидочная цена должна быть меньше обычной цены'
            })

        min_stock = attrs.get('min_stock_level', getattr(self.instance, 'min_stock_level', None))
        max_stock = attrs.get('max_stock_level', getattr(self.instance, 'max_stock_level', None))

        if min_stock and max_stock and min_stock >= max_stock:
            raise serializers.ValidationError({
                'max_stock_level': 'Максимальный уровень должен быть больше минимального'
            })

        return attrs


class ProductCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'description', 'category', 'supplier',
            'cost_price', 'selling_price', 'discount_price',
            'stock_quantity', 'min_stock_level', 'max_stock_level',
            'weight', 'dimensions', 'status', 'is_featured'
        ]

    def validate_sku(self, value):
        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("Товар с таким SKU уже существует")
        return value

    def validate_barcode(self, value):
        if value and Product.objects.filter(barcode=value).exists():
            raise serializers.ValidationError("Товар с таким штрих-кодом уже существует")
        return value

    def validate(self, attrs):
        # Проверка цен
        cost_price = attrs.get('cost_price')
        selling_price = attrs.get('selling_price')
        discount_price = attrs.get('discount_price')

        if cost_price and selling_price and selling_price <= cost_price:
            raise serializers.ValidationError({
                'selling_price': 'Цена продажи должна быть больше себестоимости'
            })

        if discount_price and selling_price and discount_price >= selling_price:
            raise serializers.ValidationError({
                'discount_price': 'Скидочная цена должна быть меньше обычной цены'
            })

        min_stock = attrs.get('min_stock_level', 0)
        max_stock = attrs.get('max_stock_level')

        if max_stock and min_stock >= max_stock:
            raise serializers.ValidationError({
                'max_stock_level': 'Максимальный уровень должен быть больше минимального'
            })

        return attrs

    def create(self, validated_data):
        product = Product.objects.create(**validated_data)
        product.sync_to_core_service()
        return product


class ProductBulkUpdateSerializer(serializers.Serializer):

    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="ID товаров для обновления"
    )
    updates = serializers.DictField(
        help_text="Поля для обновления"
    )

    def validate_product_ids(self, value):
        if not value:
            raise serializers.ValidationError("Необходимо указать хотя бы один ID товара")

        existing_ids = Product.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                f"Товары с ID {list(missing_ids)} не найдены"
            )

        return value

    def validate_updates(self, value):
        if not value:
            raise serializers.ValidationError("Необходимо указать поля для обновления")

        allowed_fields = [
            'status', 'is_featured', 'selling_price', 'discount_price',
            'min_stock_level', 'max_stock_level', 'supplier'
        ]

        invalid_fields = []
        for field in value.keys():
            if field not in allowed_fields:
                invalid_fields.append(field)

        if invalid_fields:
            raise serializers.ValidationError(
                f"Поля {invalid_fields} не разрешены для массового обновления. "
                f"Допустимые поля: {allowed_fields}"
            )

        return value


class SyncToCoreSerializer(serializers.Serializer):

    schema_id = serializers.IntegerField(
        default=2,
        min_value=1,
        help_text="ID схемы в Core Service"
    )
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="ID товаров для синхронизации (если не указано - все активные)"
    )
    include_inactive = serializers.BooleanField(
        default=False,
        help_text="Включать неактивные товары"
    )

    def validate_product_ids(self, value):
        if value:
            existing_ids = Product.objects.filter(id__in=value).values_list('id', flat=True)
            missing_ids = set(value) - set(existing_ids)

            if missing_ids:
                raise serializers.ValidationError(
                    f"Товары с ID {list(missing_ids)} не найдены"
                )

        return value


class StockUpdateSerializer(serializers.Serializer):

    OPERATION_CHOICES = [
        ('SET', 'Установить значение'),
        ('ADD', 'Добавить к текущему'),
        ('SUBTRACT', 'Вычесть из текущего'),
    ]

    product_id = serializers.IntegerField()
    operation = serializers.ChoiceField(choices=OPERATION_CHOICES)
    quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Причина изменения остатков"
    )

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Товар с указанным ID не найден")
        return value

    def validate(self, attrs):
        operation = attrs.get('operation')
        quantity = attrs.get('quantity')
        product_id = attrs.get('product_id')

        if operation == 'SUBTRACT':
            try:
                product = Product.objects.get(id=product_id)
                if product.stock_quantity < quantity:
                    raise serializers.ValidationError({
                        'quantity': f'Недостаточно товара на складе. Доступно: {product.stock_quantity}'
                    })
            except Product.DoesNotExist:
                pass

        return attrs


class ProductStatsSerializer(serializers.Serializer):

    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    featured_products = serializers.IntegerField()
    total_stock_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    categories_count = serializers.IntegerField()
    suppliers_count = serializers.IntegerField()

    status_breakdown = serializers.DictField()

    top_by_value = serializers.ListField()
    recently_added = serializers.ListField()


class ProductFilterSerializer(serializers.Serializer):

    category = serializers.IntegerField(required=False)
    supplier = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=Product.STATUS_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)
    low_stock = serializers.BooleanField(required=False)
    out_of_stock = serializers.BooleanField(required=False)
    price_min = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    price_max = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    search = serializers.CharField(required=False, max_length=200)
    ordering = serializers.ChoiceField(
        choices=[
            'name', '-name', 'sku', '-sku', 'selling_price', '-selling_price',
            'created_at', '-created_at', 'stock_quantity', '-stock_quantity'
        ],
        required=False,
        default='-created_at'
    )

    def validate(self, attrs):
        price_min = attrs.get('price_min')
        price_max = attrs.get('price_max')

        if price_min and price_max and price_min > price_max:
            raise serializers.ValidationError({
                'price_max': 'Максимальная цена должна быть больше минимальной'
            })

        return attrs

# product_service/api/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests
from django.conf import settings

from products.models import Category, Supplier, Product, ProductImage
from .serializers import (
    CategorySerializer, SupplierSerializer, ProductSerializer,
    ProductCreateSerializer, ProductImageSerializer, SyncToCoreSerializer,
    StockUpdateSerializer, ProductBulkUpdateSerializer, ProductStatsSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API для работы с категориями товаров

    Позволяет создавать иерархические категории,
    просматривать количество товаров в каждой категории.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True)

        # Фильтр по родительской категории
        parent = self.request.query_params.get('parent', None)
        if parent is not None:
            if parent == 'null' or parent == '':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent)

        return queryset.prefetch_related('products')

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        category = self.get_object()
        products = Product.objects.filter(category=category, status='ACTIVE')

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    API для работы с поставщиками

    Управление информацией о поставщиках и их товарами.
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_person', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = Supplier.objects.filter(is_active=True)
        return queryset.prefetch_related('products')

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        supplier = self.get_object()
        products = Product.objects.filter(supplier=supplier)

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API для работы с товарами

    Полный CRUD для товаров с дополнительными возможностями:
    - Фильтрация и поиск
    - Управление остатками
    - Синхронизация с Core Service
    - Массовые операции
    """

    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'barcode', 'description']
    ordering_fields = ['name', 'sku', 'selling_price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']

    # Фильтры
    filterset_fields = {
        'category': ['exact'],
        'supplier': ['exact'],
        'status': ['exact'],
        'is_featured': ['exact'],
        'selling_price': ['gte', 'lte'],
        'stock_quantity': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'supplier').prefetch_related('images')

        # Фильтр по низким остаткам
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            queryset = queryset.filter(stock_quantity__lte=F('min_stock_level'))

        # Фильтр по отсутствию на складе
        out_of_stock = self.request.query_params.get('out_of_stock', None)
        if out_of_stock == 'true':
            queryset = queryset.filter(stock_quantity=0)

        # Фильтр по ценовому диапазону
        price_min = self.request.query_params.get('price_min', None)
        price_max = self.request.query_params.get('price_max', None)

        if price_min:
            queryset = queryset.filter(selling_price__gte=price_min)
        if price_max:
            queryset = queryset.filter(selling_price__lte=price_max)

        return queryset

    @swagger_auto_schema(
        operation_description="Синхронизация товаров с Core Service",
        request_body=SyncToCoreSerializer,
        responses={
            200: openapi.Response('Синхронизация выполнена успешно'),
            502: openapi.Response('Ошибка Core Service'),
            503: openapi.Response('Core Service недоступен'),
        }
    )
    @action(detail=False, methods=['post'])
    def sync_to_core(self, request):
        serializer = SyncToCoreSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        schema_id = validated_data.get('schema_id', 2)
        product_ids = validated_data.get('product_ids', None)
        include_inactive = validated_data.get('include_inactive', False)

        queryset = Product.objects.select_related('category', 'supplier')

        if product_ids:
            queryset = queryset.filter(id__in=product_ids)

        if not include_inactive:
            queryset = queryset.filter(status='ACTIVE')

        if not queryset.exists():
            return Response({
                'error': 'Не найдено товаров для синхронизации'
            }, status=status.HTTP_404_NOT_FOUND)

        data_list = [product.to_table_data() for product in queryset]

        try:
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/schemas/{schema_id}/populate/",
                json={
                    "source_service": "product_service",
                    "data": data_list
                },
                timeout=30
            )

            if response.status_code == 201:
                return Response({
                    'message': f'Синхронизировано {len(data_list)} товаров',
                    'count': len(data_list),
                    'schema_id': schema_id
                })
            else:
                return Response({
                    'error': f'Ошибка Core Service: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_502_BAD_GATEWAY)

        except requests.RequestException as e:
            return Response({
                'error': f'Не удалось подключиться к Core Service: {str(e)}'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @swagger_auto_schema(
        operation_description="Обновление остатков товара",
        request_body=StockUpdateSerializer
    )
    @action(detail=False, methods=['post'])
    def update_stock(self, request):
        serializer = StockUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        product_id = validated_data['product_id']
        operation = validated_data['operation']
        quantity = validated_data['quantity']
        reason = validated_data.get('reason', '')

        try:
            product = Product.objects.get(id=product_id)
            old_quantity = product.stock_quantity

            if operation == 'SET':
                product.stock_quantity = quantity
            elif operation == 'ADD':
                product.stock_quantity += quantity
            elif operation == 'SUBTRACT':
                new_quantity = product.stock_quantity - quantity
                if new_quantity < 0:
                    return Response({
                        'error': 'Недостаточно товара на складе'
                    }, status=status.HTTP_400_BAD_REQUEST)
                product.stock_quantity = new_quantity

            product.save()

            # Синхронизация с Core Service
            product.sync_to_core_service()

            return Response({
                'message': 'Остатки обновлены успешно',
                'product': product.name,
                'old_quantity': old_quantity,
                'new_quantity': product.stock_quantity,
                'operation': operation,
                'reason': reason
            })

        except Product.DoesNotExist:
            return Response({
                'error': 'Товар не найден'
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Массовое обновление товаров",
        request_body=ProductBulkUpdateSerializer
    )
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        serializer = ProductBulkUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        product_ids = validated_data['product_ids']
        updates = validated_data['updates']

        try:
            with transaction.atomic():
                updated_count = Product.objects.filter(
                    id__in=product_ids
                ).update(**updates)

                # Синхронизация обновленных товаров
                updated_products = Product.objects.filter(id__in=product_ids)
                for product in updated_products:
                    product.sync_to_core_service()

                return Response({
                    'message': f'Обновлено {updated_count} товаров',
                    'updated_fields': list(updates.keys())
                })

        except Exception as e:
            return Response({
                'error': f'Ошибка при массовом обновлении: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по товарам"""

        # Основная статистика
        total_products = Product.objects.count()
        active_products = Product.objects.filter(status='ACTIVE').count()
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=F('min_stock_level')
        ).count()
        out_of_stock_products = Product.objects.filter(stock_quantity=0).count()
        featured_products = Product.objects.filter(is_featured=True).count()

        # Стоимость остатков
        total_stock_value = Product.objects.filter(
            status='ACTIVE'
        ).aggregate(
            total_value=Sum(F('stock_quantity') * F('cost_price'))
        )['total_value'] or 0

        # Статистика по статусам
        status_breakdown = dict(
            Product.objects.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )

        # Количество категорий и поставщиков
        categories_count = Category.objects.filter(is_active=True).count()
        suppliers_count = Supplier.objects.filter(is_active=True).count()

        # ТОП товары по стоимости остатков
        top_by_value = Product.objects.filter(
            status='ACTIVE'
        ).annotate(
            stock_value=F('stock_quantity') * F('cost_price')
        ).order_by('-stock_value')[:10].values(
            'name', 'sku', 'stock_quantity', 'cost_price', 'stock_value'
        )

        # Недавно добавленные товары
        recently_added = Product.objects.order_by('-created_at')[:10].values(
            'name', 'sku', 'category__name', 'created_at'
        )

        stats_data = {
            'total_products': total_products,
            'active_products': active_products,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
            'featured_products': featured_products,
            'total_stock_value': total_stock_value,
            'categories_count': categories_count,
            'suppliers_count': suppliers_count,
            'status_breakdown': status_breakdown,
            'top_by_value': list(top_by_value),
            'recently_added': list(recently_added)
        }

        serializer = ProductStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sync_single(self, request, pk=None):
        """Синхронизация одного товара с Core Service"""
        product = self.get_object()
        success = product.sync_to_core_service()

        if success:
            return Response({
                'message': f'Товар "{product.name}" синхронизирован'
            })
        else:
            return Response({
                'error': 'Ошибка синхронизации'
            }, status=status.HTTP_502_BAD_GATEWAY)


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    API для работы с изображениями товаров
    """

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

    def get_queryset(self):
        queryset = ProductImage.objects.select_related('product')

        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset.order_by('-is_primary', '-created_at')

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        image = self.get_object()

        ProductImage.objects.filter(
            product=image.product,
            is_primary=True
        ).update(is_primary=False)

        image.is_primary = True
        image.save()

        return Response({
            'message': 'Изображение установлено как основное'
        })

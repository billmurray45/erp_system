from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from users.models import User
from .serializers import UserSerializer, UserCreateSerializer, SyncToCoreSerializer
import requests
from django.conf import settings


class UserViewSet(viewsets.ModelViewSet):
    """
    API для работы с пользователями

    Позволяет создавать, читать, обновлять и удалять пользователей.
    Также предоставляет возможность синхронизации с Core Service.
    """

    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')

        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department=department)

        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)

        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            ) | queryset.filter(
                username__icontains=search
            )

        return queryset

    @swagger_auto_schema(
        operation_description="Синхронизация пользователей с Core Service",
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
        schema_id = validated_data.get('schema_id', 1)
        user_ids = validated_data.get('user_ids', None)

        if user_ids:
            users = User.objects.filter(id__in=user_ids, is_active=True)
        else:
            users = User.objects.filter(is_active=True)

        if not users.exists():
            return Response({
                'error': 'Не найдено пользователей для синхронизации'
            }, status=status.HTTP_404_NOT_FOUND)

        data_list = [user.to_table_data() for user in users]

        try:
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/schemas/{schema_id}/populate/",
                json={
                    "source_service": "user_service",
                    "data": data_list
                },
                timeout=10
            )

            if response.status_code == 201:
                return Response({
                    'message': f'Синхронизировано {len(data_list)} пользователей',
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

    @action(detail=True, methods=['post'])
    def sync_single(self, request, pk=None):
        user = self.get_object()
        success = user.sync_to_core_service()

        if success:
            return Response({
                'message': f'Пользователь {user.full_name} синхронизирован'
            })
        else:
            return Response({
                'error': 'Ошибка синхронизации'
            }, status=status.HTTP_502_BAD_GATEWAY)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TableSchemaViewSet, TableDataViewSet

router = DefaultRouter()
router.register(r'schemas', TableSchemaViewSet)
router.register(r'data', TableDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),
]

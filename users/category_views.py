"""Public category list view for providers"""
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from users.models import Category


class PublicCategoryListView(generics.ListAPIView):
    """List active categories for employers/providers to select when creating jobs/trainings"""
    
    class CategoryListSerializer(serializers.ModelSerializer):
        class Meta:
            model = Category
            fields = ['id', 'name', 'slug', 'description']
    
    serializer_class = CategoryListSerializer
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.filter(is_active=True).order_by('name')

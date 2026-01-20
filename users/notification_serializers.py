from rest_framework import serializers
from .notification_models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'data',
            'is_read',
            'created_at',
        ]
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'data', 'created_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification list"""
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'is_read',
            'created_at',
            'time_ago',
            'data',
        ]
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() // 60)
            return f'{mins}m ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() // 3600)
            return f'{hours}h ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d')


class UnreadCountSerializer(serializers.Serializer):
    """Serializer for unread count response"""
    unread_count = serializers.IntegerField()

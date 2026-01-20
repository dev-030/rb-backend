from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .notification_models import Notification
from .notification_serializers import NotificationListSerializer, UnreadCountSerializer


class NotificationListView(generics.ListAPIView):
    """List all notifications for the authenticated user"""
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationUnreadCountView(APIView):
    """Get count of unread notifications"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class MarkNotificationReadView(APIView):
    """Mark a single notification as read"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user
            )
            notification.mark_as_read()
            return Response({'status': 'marked as read'})
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class MarkAllNotificationsReadView(APIView):
    """Mark all notifications as read for the authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({
            'status': 'success',
            'marked_count': count
        })


class DeleteNotificationView(APIView):
    """Delete a single notification"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user
            )
            notification.delete()
            return Response({'status': 'deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClearAllNotificationsView(APIView):
    """Delete all notifications for the authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        count, _ = Notification.objects.filter(recipient=request.user).delete()
        return Response({
            'status': 'success',
            'deleted_count': count
        })

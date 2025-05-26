from django.contrib import admin
from django.urls import path
from notifications.views import NotificationAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/send-notification/', NotificationAPIView.as_view(), name='send-notification'),
]
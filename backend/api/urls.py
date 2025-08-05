from django.urls import path
from . import views
from .views import VerifyKhaltiPayment

urlpatterns = [
    # ... other URLs ...
    path('admin/popular-items/', views.get_popular_items, name='popular-items'),
    path('admin/orders/<int:order_id>/', views.delete_order, name='delete-order'),
    path('orders/<int:order_id>/acknowledge/', views.acknowledge_order, name='acknowledge-order'),
    path('payment/verify-khalti/', VerifyKhaltiPayment.as_view(), name='verify-khalti'),
    path('auth/request-reset-code/', views.request_reset_code, name='request-reset-code'),
    path('auth/verify-reset-code/', views.verify_reset_code, name='verify-reset-code'),
    path('user/profile/', views.user_profile, name='user-profile'),
]
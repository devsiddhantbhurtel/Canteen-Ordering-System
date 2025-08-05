from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import HttpResponseRedirect
from .views import (
    RegisterView, login_view, logout_view, FoodItemViewSet,
    OrderViewSet, FeedbackViewSet, PaymentViewSet, generate_qr_code, rfid_scan,
    verify_token, verify_email, admin_summary,
    AdminFoodItemViewSet, AdminUserViewSet, AdminOrderViewSet, CartViewSet,
    initiate_khalti_payment, verify_khalti_payment, get_khalti_config,
    get_popular_items, get_user_orders, update_order_status,
    process_order_payment, complete_order_payment, cancel_order_payment,
    get_user_info, admin_dashboard_summary, process_order, cancel_order, complete_order,
    admin_create_user, NotificationListView, NotificationDetailView
)

router = DefaultRouter()
router.register(r'food-items', FoodItemViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'payments', PaymentViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'admin/food-items', AdminFoodItemViewSet, basename='admin-fooditem')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')
router.register(r'admin/orders', AdminOrderViewSet, basename='admin-order')

def redirect_foods(request):
    return HttpResponseRedirect('/api/food-items/')

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify/', verify_email, name='verify-email'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/verify-token/', verify_token, name='verify-token'),
    path('admin/summary/', admin_summary, name='admin-summary'),
    path('admin/popular-items/', get_popular_items, name='popular-items'),
    path('admin/create-user/', admin_create_user, name='admin-create-user'),
    path('payment/khalti-config/', get_khalti_config, name='khalti-config'),
    path('payment/initiate-khalti/', initiate_khalti_payment, name='initiate-khalti'),
    # path('payment/verify-khalti/', verify_khalti_payment, name='verify-khalti'),
    path('qr/', generate_qr_code, name='generate_qr'),
    path('rfid/', rfid_scan, name='rfid_scan'),
    path('foods/', redirect_foods, name='redirect-foods'),
    path('orders/track/', get_user_orders, name='track_orders'),
    path('orders/<int:order_id>/update-status/', update_order_status, name='update_order_status'),
    path('orders/<int:order_id>/process-payment/', process_order_payment, name='process_order_payment'),
    path('orders/<int:order_id>/complete-payment/', complete_order_payment, name='complete_order_payment'),
    path('orders/<int:order_id>/cancel-payment/', cancel_order_payment, name='cancel_order_payment'),
    path('users/me/', get_user_info, name='user-info'),
    path('admin/dashboard/summary/', admin_dashboard_summary, name='admin-dashboard-summary'),
    path('orders/<int:order_id>/process/', process_order, name='process_order'),
    path('orders/<int:order_id>/cancel/', cancel_order, name='cancel_order'),
    path('orders/<int:order_id>/complete/', complete_order, name='complete_order'),
]

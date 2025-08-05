from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, F
from canteen_app.models import FoodItem, Order, OrderDetail
from django.contrib.auth.models import User
from canteen_app.models import UserProfile
from django.utils import timezone
from datetime import timedelta
import random
from django.core.mail import send_mail
from .serializers import UserProfileSerializer

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_popular_items(request):
    # First check if there are any orders
    if not OrderDetail.objects.exists():
        return Response([])  # Return empty list if no orders exist
        
    popular_items = FoodItem.objects.annotate(
        order_count=Sum('orderdetail__quantity', default=0),
        total_revenue=Sum(F('orderdetail__quantity') * F('price'), default=0)
    ).filter(
        orderdetail__quantity__gt=0  # Only include items that have orders with quantity > 0
    ).exclude(
        order_count=0  # Exclude items with no orders
    ).distinct().order_by('-order_count')[:5]
    
    # Double check to ensure we don't return items with no orders
    data = [{
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'order_count': item.order_count,
        'total_revenue': item.total_revenue
    } for item in popular_items if item.order_count > 0]
    
    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        # Delete all order details first
        OrderDetail.objects.filter(order=order).delete()
        
        # Then delete the order
        order.delete()
        
        return Response({'message': 'Order deleted successfully'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order.order_status = 'completed'
        order.save()
        return Response({'message': 'Order acknowledged and marked as completed.'}, status=200)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_reset_code(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=400)
    try:
        user = User.objects.get(email=email)
        profile = user.profile
        # Generate a 6-digit code
        code = f'{random.randint(100000, 999999)}'
        profile.reset_code = code
        profile.reset_code_expiry = timezone.now() + timedelta(minutes=15)
        profile.save()
        send_mail(
            'Your Password Reset Code',
            f'Your password reset code is: {code}',
            'no-reply@canteen.com',
            [email],
            fail_silently=False,
        )
        return Response({'message': 'Reset code sent to email.'})
    except User.DoesNotExist:
        return Response({'error': 'No user with that email.'}, status=404)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_code(request):
    email = request.data.get('email')
    code = request.data.get('code')
    new_password = request.data.get('new_password')
    if not (email and code and new_password):
        return Response({'error': 'Email, code, and new password are required.'}, status=400)
    try:
        user = User.objects.get(email=email)
        profile = user.profile
        if (profile.reset_code != code or not profile.reset_code_expiry or profile.reset_code_expiry < timezone.now()):
            return Response({'error': 'Invalid or expired code.'}, status=400)
        user.set_password(new_password)
        user.save()
        # Clear code
        profile.reset_code = None
        profile.reset_code_expiry = None
        profile.save()
        return Response({'message': 'Password reset successful.'})
    except User.DoesNotExist:
        return Response({'error': 'No user with that email.'}, status=404)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile = request.user.profile
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class VerifyKhaltiPayment(APIView):
    def post(self, request):
        pidx = request.data.get('pidx')
        if not pidx:
            return Response({'status': 'error', 'message': 'Missing payment ID'}, status=400)
        # Placeholder for actual Khalti verification logic
        return Response({'status': 'success', 'message': 'Payment verified'}, status=200)
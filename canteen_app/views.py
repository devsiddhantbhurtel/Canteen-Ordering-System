# canteen_app/views.py
from rest_framework import viewsets, status, permissions, generics, serializers
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
import qrcode
from io import BytesIO
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
import logging
import time
import json
import uuid
import requests
from django.http import JsonResponse
from urllib.parse import urlencode
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import Count, Sum, F, Avg, Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

# Import your models
from .models import PhoneVerification, FoodItem, Order, Feedback, Payment, Cart, OrderDetail, UserProfile, Notification
# Import your serializers
from .serializers import (
    RegisterSerializer, UserSerializer, FoodItemSerializer,
    OrderSerializer, FeedbackSerializer, PaymentSerializer, AdminUserSerializer,
    CartSerializer
)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'Please provide both username and password'}, status=400)
    
    # Print debug information
    print(f"Login attempt for username: {username}")
    
    # Check if user exists
    try:
        user_exists = User.objects.filter(username=username).exists()
        if not user_exists:
            print(f"User {username} does not exist")
            return Response({'error': 'Invalid credentials'}, status=400)
    except Exception as e:
        print(f"Error checking if user exists: {str(e)}")
    
    # Try to authenticate
    user = authenticate(username=username, password=password)
    
    if user:
        print(f"Authentication successful for user: {username}")
        
        # Ensure user has a profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': 'admin' if user.is_superuser else 'student'}
        )
        
        # Ensure user is active
        if not user.is_active:
            user.is_active = True
            user.save()
            print(f"User {username} was inactive, activated now")
        
        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        
        # Get user data with role
        user_data = UserSerializer(user).data
        
        # Add role information to user data
        user_data['role'] = profile.role
        
        print(f"Login successful for user: {username}, role: {profile.role}")
        
        return Response({
            'token': token.key,
            'user': user_data
        })
    
    print(f"Authentication failed for username: {username}")
    return Response({'error': 'Invalid credentials'}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    request.user.auth_token.delete()
    logout(request)
    return Response({'message': 'Successfully logged out'})

class FoodItemViewSet(viewsets.ModelViewSet):
    queryset = FoodItem.objects.all()
    serializer_class = FoodItemSerializer
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().order_by('-order_time')
        return Order.objects.filter(user=user).order_by('-order_time')

    def create(self, request, *args, **kwargs):
        try:
            # Get data from request
            order_details = request.data.get('order_details', [])
            payment_method = request.data.get('payment_method', 'cod')
            pickup_time = request.data.get('pickup_time')
            is_offline = request.data.get('is_offline', True)
            created_for = request.data.get('created_for')  # Get the user ID for whom the order is created

            # If this is an offline order and created_for is provided, use that user
            user = request.user
            if is_offline and created_for:
                try:
                    user = User.objects.get(id=created_for)
                except User.DoesNotExist:
                    user = request.user
            
            # Create the order
            order = Order.objects.create(
                user=user,
                payment_method=payment_method,
                payment_status='pending',
                order_status='received',
                pickup_time=pickup_time,
                is_offline=is_offline
            )
            total_amount = 0
            for detail_data in order_details:
                food_item = FoodItem.objects.get(id=detail_data['food_item_id'])
                quantity = detail_data.get('quantity', 1)
                customization = detail_data.get('customization', {})
                OrderDetail.objects.create(
                    order=order,
                    food_item=food_item,
                    food_item_name=food_item.name,
                    food_item_price=food_item.price,
                    quantity=quantity,
                    customization=str(customization)
                )
                total_amount += float(food_item.price) * quantity
            
            order.save()
            # Notify all admins
            admin_users = User.objects.filter(is_staff=True)
            for admin in admin_users:
                Notification.objects.create(
                    recipient=admin,
                    message=f"New order placed by {user.username} (Order ID: {order.id})"
                )
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        # Check if this is an offline order with a specific user
        created_for = self.request.data.get('created_for')
        if created_for and self.request.data.get('is_offline'):
            try:
                user = User.objects.get(id=created_for)
                serializer.save(user=user)
            except User.DoesNotExist:
                serializer.save(user=self.request.user)
        else:
            serializer.save(user=self.request.user)

class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Feedback.objects.all().select_related('user', 'food_item', 'order').order_by('-created_at')
        return Feedback.objects.filter(user=self.request.user).select_related('user', 'food_item', 'order').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    queryset = Cart.objects.all()

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def get_cart(self, request):
        """Get the current user's cart items"""
        cart_items = self.get_queryset()
        serializer = self.get_serializer(cart_items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_quantity(self, request, pk=None):
        """Update the quantity of a cart item"""
        try:
            cart_item = self.get_object()
            action = request.data.get('action')
            
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                return Response(
                    {'error': 'Invalid action or quantity cannot be less than 1'},
                    status=400
                )
            
            cart_item.save()
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all items from the user's cart"""
        try:
            self.get_queryset().delete()
            return Response({'message': 'Cart cleared successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class AdminFoodItemViewSet(viewsets.ModelViewSet):
    queryset = FoodItem.objects.all()
    serializer_class = FoodItemSerializer
    permission_classes = [IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        try:
            # Get all users with their profiles
            queryset = User.objects.all().select_related('profile')
            
            # Find users without profiles
            users_without_profiles = []
            for user in queryset:
                if not hasattr(user, 'profile'):
                    users_without_profiles.append(
                        UserProfile(
                            user=user,
                            role='student',
                            contact=None
                        )
                    )
            
            # Bulk create profiles if needed
            if users_without_profiles:
                UserProfile.objects.bulk_create(users_without_profiles)
                # Refresh queryset to include new profiles
                queryset = User.objects.all().select_related('profile')
            
            # Serialize the data
            serializer = self.get_serializer(queryset, many=True)
            
            # Check for users without contact info
            users_without_contact = [
                user.username for user in queryset 
                if hasattr(user, 'profile') and not user.profile.contact
            ]
            
            if users_without_contact:
                return Response({
                    'data': serializer.data,
                    'warning': 'Some users are missing contact information. Please update their contact details.',
                    'users_missing_contact': users_without_contact
                })
            
            return Response(serializer.data)
            
        except Exception as e:
            import traceback
            print(f"Error in AdminUserViewSet.list: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': 'An error occurred while fetching users. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_summary(request):
    try:
        total_users = User.objects.filter(is_superuser=False).count()
        total_orders = Order.objects.count()
        total_revenue = OrderDetail.objects.filter(
            order__payment_status='completed'
        ).aggregate(
            total=Sum(F('food_item__price') * F('quantity'))
        )['total'] or 0
        return Response({
            "total_users": total_users,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue)
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    verification_code = request.data.get('token')  # Get from request body
    try:
        verification = PhoneVerification.objects.get(verification_code=verification_code)
        if not verification.verified:  # Check if not already verified
            user = verification.user
            user.is_active = True
            user.save()
            verification.verified = True
            verification.save()
            return Response({'message': 'Email verified successfully'})
        return Response({'error': 'Verification code has already been used'}, status=400)
    except PhoneVerification.DoesNotExist:
        return Response({'error': 'Invalid verification code'}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    return Response({'message': 'Token is valid'})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_summary(request):
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    return Response({
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_popular_items(request):
    # Get all food items with their order details
    popular_items = FoodItem.objects.annotate(
        order_count=Sum('orderdetail__quantity'),
        total_revenue=Sum(F('orderdetail__quantity') * F('price'))
    ).order_by('-order_count')

    # Convert to list format
    data = []
    for item in popular_items:
        if item.order_count:  # Only include items that have been ordered
            data.append({
                'id': item.id,
                'name': item.name,
                'price': float(item.price),
                'order_count': item.order_count or 0,
                'total_revenue': float(item.total_revenue or 0)
            })

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_time')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.data.get('status')
        if new_status:
            order.order_status = new_status
            order.save()
            # NOTIFY USER IF ORDER IS READY
            if new_status == 'ready':
                Notification.objects.create(
                    recipient=order.user,
                    message=f"Your order (Order ID: {order.id}) is ready for pickup!"
                )
            return Response({'message': f'Order status updated to {new_status}'})
        return Response({'error': 'Status not provided'}, status=400)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def generate_qr_code(request):
    data = request.GET.get('data', '')
    img = qrcode.make(data)
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response

@api_view(['POST'])
@permission_classes([AllowAny])
def rfid_scan(request):
    rfid_id = request.data.get('rfid_id')
    if not rfid_id:
        return Response({'error': 'RFID ID is required'}, status=400)
    
    try:
        # Find user by RFID ID
        profile = UserProfile.objects.select_related('user').get(rfid_id=rfid_id)
        user = profile.user
        
        # Update last scan time
        profile.last_rfid_scan = timezone.now()
        profile.save()
        
        # Create or get token
        token, _ = Token.objects.get_or_create(user=user)
        
        # Get user data
        user_data = UserSerializer(user).data
        # Add contact information
        user_data['contact_number'] = profile.contact
        
        return Response({
            'token': token.key,
            'user': user_data,
            'message': f'Successfully logged in as {user.username}'
        })
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Invalid RFID card. Please contact administrator.'
        }, status=404)
    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_order_payment(request, order_id):
    """Process a payment for an order"""
    try:
        order = Order.objects.get(id=order_id)
        if order.payment_status == 'completed':
            return Response({'error': 'Payment already completed'}, status=400)
            
        # Update payment status to completed
        order.payment_status = 'completed'
        order.save()
        
        return Response({
            'message': 'Payment completed successfully',
            'order': OrderSerializer(order).data
        })
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_order_payment(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        if order.payment_status != 'processing':
            return Response({'error': 'Order not in processing state'}, status=400)
        order.payment_status = 'completed'
        order.save()
        return Response({'message': 'Payment completed successfully'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order_payment(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        if order.payment_status == 'completed':
            return Response({'error': 'Cannot cancel completed payment'}, status=400)
        order.payment_status = 'cancelled'
        order.save()
        return Response({'message': 'Payment cancelled successfully'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_khalti_config(request):
    """Return Khalti configuration for frontend"""
    return Response({
        'publicKey': settings.KHALTI_PUBLIC_KEY
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_khalti_payment(request):
    """Initiate a Khalti payment"""
    try:
        amount = request.data.get('amount')
        order_id = request.data.get('order_id')
        
        if not amount or not order_id:
            return Response({'error': 'Amount and order_id are required'}, status=400)
        
        # Get order and verify ownership
        try:
            order = Order.objects.select_related('user').get(id=order_id)
            if order.user != request.user:
                return Response({'error': 'You are not authorized to pay for this order'}, status=403)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        # Get user information from the authenticated user
        user = request.user
        user_name = user.get_full_name() or user.username
        user_email = user.email or ''
        user_phone = user.profile.contact if hasattr(user, 'profile') and user.profile.contact else "9800000000"

        # Convert amount to paisa
        amount_in_paisa = int(float(amount) * 100)
        
        # Prepare the payload for Khalti API
        payload = {
            "return_url": f"{settings.FRONTEND_URL}/payment/verify/",
            "website_url": settings.FRONTEND_URL,
            "amount": amount_in_paisa,
            "purchase_order_id": str(order.id),
            "purchase_order_name": f"Order #{order.id}",
            "customer_info": {
                "name": user_name,
                "email": user_email,
                "phone": user_phone
            },
            "merchant_extra": {
                "order_id": str(order.id),
                "user_id": str(user.id)
            },
            "amount_breakdown": [
                {
                    "label": f"Order #{order.id} Amount",
                    "amount": amount_in_paisa
                }
            ],
            "product_details": [
                {
                    "identity": str(order.id),
                    "name": f"Order #{order.id}",
                    "total_price": amount_in_paisa,
                    "quantity": 1,
                    "unit_price": amount_in_paisa
                }
            ]
        }

        # Make request to Khalti API
        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        url = f"{settings.KHALTI_API_URL}/epayment/initiate/"
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                amount=amount,
                method='khalti',
                status='pending',
                khalti_pidx=response_data.get('pidx')
            )
            
            return Response({
                'status': 'success',
                'payment_url': response_data.get('payment_url')
            })
        else:
            error_msg = response.text
            try:
                error_json = json.loads(error_msg)
                error_msg = error_json.get('detail', error_msg)
            except:
                pass
            return Response(
                {'error': f'Failed to initiate Khalti payment: {error_msg}'},
                status=response.status_code
            )
            
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_khalti_payment(request):
    """Verify a Khalti payment"""
    try:
        pidx = request.data.get('pidx')
        if not pidx:
            return Response({'error': 'pidx is required'}, status=400)

        # Find payment by pidx
        try:
            payment = Payment.objects.select_related('order', 'order__user').get(khalti_pidx=pidx)
            order = payment.order
            
            # Verify that the order belongs to the requesting user
            if order.user != request.user:
                logging.error(f"User {request.user.username} attempted to verify payment for order {order.id} belonging to user {order.user.username}")
                return Response({'error': 'This order does not belong to you'}, status=403)
                
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=404)

        # Make request to Khalti API
        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        url = f"{settings.KHALTI_API_URL}/epayment/status/"
        response = requests.get(
            url,
            headers=headers,
            params={'pidx': pidx}
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Update payment status based on Khalti response
            if response_data.get('status') == 'Completed':
                # Update payment record
                payment.status = 'completed'
                payment.khalti_transaction_id = response_data.get('transaction_id')
                payment.save()
                
                # Update order payment status to completed
                order.payment_status = 'completed'
                order.save()
                
                # Notify through WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"order_{order.id}",
                    {
                        "type": "order_status_update",
                        "message": {
                            "order_id": order.id,
                            "payment_status": "completed",
                            "status": "Payment completed successfully"
                        }
                    }
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Payment verified successfully',
                    'order': OrderSerializer(order).data
                })
            else:
                # Keep payment status as pending if verification fails
                return Response({
                    'status': 'failed',
                    'message': f"Payment verification failed. Status: {response_data.get('status')}"
                })
        else:
            error_msg = response.text
            try:
                error_json = json.loads(error_msg)
                if 'detail' in error_json:
                    error_msg = error_json['detail']
            except:
                pass
            return Response(
                {'error': f"Failed to verify Khalti payment: {error_msg}"},
                status=response.status_code
            )
            
    except Exception as e:
        logging.error(f"Error in verify_khalti_payment: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_order(request, order_id):
    """Process an order (change status to preparing)"""
    try:
        print(f"Processing order {order_id}")
        order = Order.objects.get(id=order_id)
        print(f"Found order. Current status: {order.order_status}")
        
        # Update order status to preparing
        order.order_status = 'preparing'
        order.save()
        print(f"Updated order {order_id} status to preparing")
        
        # Return the updated order data
        serializer = OrderSerializer(order)
        print(f"Returning serialized data: {serializer.data}")
        return Response(serializer.data, status=200)
        
    except Order.DoesNotExist:
        print(f"Order {order_id} not found")
        return Response({'error': 'Order not found'}, status=404)
    except Exception as e:
        print(f"Error processing order {order_id}: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order"""
    try:
        order = Order.objects.get(id=order_id)
        if order.order_status in ['received', 'preparing']:
            order.order_status = 'cancelled'
            order.save()
            
            # Notify through WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{order.id}",
                {
                    "type": "order_status_update",
                    "message": {
                        "order_id": order.id,
                        "order_status": "cancelled",
                        "status": "Order has been cancelled"
                    }
                }
            )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        return Response(
            {'error': 'Cannot cancel order. Order must be in received or preparing state.'},
            status=400
        )
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    """Complete an order (change status to completed)"""
    try:
        order = Order.objects.get(id=order_id)
        if order.order_status == 'ready':
            order.order_status = 'completed'
            order.save()
            
            # Notify through WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{order.id}",
                {
                    "type": "order_status_update",
                    "message": {
                        "order_id": order.id,
                        "order_status": "completed",
                        "status": "Order has been completed"
                    }
                }
            )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        return Response(
            {'error': 'Cannot complete order. Order must be in ready state.'},
            status=400
        )
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return User.objects.all().select_related('profile')

    def create(self, request, *args, **kwargs):
        data = request.data
        created_user = None
        try:
            # Validate required fields
            if not data.get('username') or not data.get('email') or not data.get('password'):
                return Response(
                    {'error': 'Username, email and password are required fields'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate contact number
            contact = data.get('contact', '').strip()
            if not contact or not contact.isdigit() or len(contact) != 10:
                return Response(
                    {'error': 'A valid 10-digit contact number is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if contact is already in use
            if UserProfile.objects.filter(contact=contact).exists():
                return Response(
                    {'error': 'This contact number is already registered'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user with properly hashed password
            created_user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                is_active=True,
                is_staff=data.get('is_staff', False),
                is_superuser=data.get('is_superuser', False)
            )
            
            # Create profile with validated contact
            UserProfile.objects.create(
                user=created_user,
                role=data.get('role', 'student').lower(),
                contact=contact,
                rfid_id=data.get('rfid_id')
            )
            
            # Double-check password hashing
            created_user.set_password(data['password'])
            created_user.save()
            
            # Verify the user can authenticate with the provided credentials
            test_auth = authenticate(username=data['username'], password=data['password'])
            if not test_auth:
                print(f"Warning: User {data['username']} was created but authentication test failed")
                # If authentication test fails, try one more time with a different approach
                from django.contrib.auth.hashers import make_password
                created_user.password = make_password(data['password'])
                created_user.save()
                print(f"Password reset using make_password for user {data['username']}")
            
            serializer = self.get_serializer(created_user)
            return Response({
                'data': serializer.data,
                'message': 'User created successfully.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # If user creation fails, clean up if necessary
            if created_user:
                created_user.delete()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        data = request.data
        try:
            # Validate contact if provided
            if 'contact' in data:
                contact = data['contact'].strip()
                if not contact or not contact.isdigit() or len(contact) != 10:
                    return Response(
                        {'error': 'A valid 10-digit contact number is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Check if contact is already in use by another user
                existing_profile = UserProfile.objects.filter(contact=contact).exclude(user=user).first()
                if existing_profile:
                    return Response(
                        {'error': 'This contact number is already registered to another user'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Update user fields
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            if data.get('password'):
                user.set_password(data['password'])
            user.is_active = data.get('is_active', user.is_active)
            user.is_staff = data.get('is_staff', user.is_staff)
            user.is_superuser = data.get('is_superuser', user.is_superuser)
            user.save()
            
            # Update profile
            profile = user.profile
            if 'role' in data:
                profile.role = data['role'].lower()
            if 'contact' in data:
                profile.contact = contact
            if 'rfid_id' in data:
                profile.rfid_id = data['rfid_id']
            profile.save()
            
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_create_user(request):
    """
    Special endpoint for admin user creation that ensures passwords are properly hashed.
    """
    data = request.data
    created_user = None
    
    try:
        # Validate required fields
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return Response(
                {'error': 'Username, email and password are required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate contact number
        contact = data.get('contact', '').strip()
        if not contact or not contact.isdigit() or len(contact) != 10:
            return Response(
                {'error': 'A valid 10-digit contact number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if contact is already in use
        if UserProfile.objects.filter(contact=contact).exists():
            return Response(
                {'error': 'This contact number is already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user with properly hashed password
        created_user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            is_active=True,
            is_staff=data.get('is_staff', False),
            is_superuser=data.get('is_superuser', False)
        )
        
        # Create profile with validated contact
        UserProfile.objects.create(
            user=created_user,
            role=data.get('role', 'student').lower(),
            contact=contact,
            rfid_id=data.get('rfid_id')
        )
        
        # Double-check password hashing
        created_user.set_password(data['password'])
        created_user.save()
        
        # Verify the user can authenticate with the provided credentials
        test_auth = authenticate(username=data['username'], password=data['password'])
        if not test_auth:
            print(f"Warning: User {data['username']} was created but authentication test failed")
            # If authentication test fails, try one more time with a different approach
            from django.contrib.auth.hashers import make_password
            created_user.password = make_password(data['password'])
            created_user.save()
            print(f"Password reset using make_password for user {data['username']}")
        
        serializer = AdminUserSerializer(created_user)
        return Response({
            'data': serializer.data,
            'message': 'User created successfully.'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        # If user creation fails, clean up if necessary
        if created_user:
            created_user.delete()
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        ) 

from rest_framework.views import APIView
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Fetch notifications as before
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        notif_data = [
            {
                'id': n.id,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at
            } for n in notifications
        ]
        # Fetch all 'ready' orders for this user and add as notifications
        from .models import Order
        ready_orders = Order.objects.filter(user=request.user, order_status='ready').order_by('-order_time')
        for order in ready_orders:
            notif_data.append({
                'id': f'order-ready-{order.id}',
                'message': f'Your order (Order ID: {order.id}) is ready for pickup!',
                'is_read': False,
                'created_at': order.order_time
            })
        # Sort all notifications by created_at descending
        notif_data.sort(key=lambda x: x['created_at'], reverse=True)
        return Response(notif_data)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification

class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        print(f"[DEBUG] Notification PATCH attempt: pk={pk}, user={request.user}")
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            print(f"[DEBUG] Notification not found: pk={pk}, user={request.user}")
            return Response({'error': 'Notification not found'}, status=404)
        notif.is_read = request.data.get('is_read', notif.is_read)
        notif.save()
        print(f"[DEBUG] Notification marked as read: pk={pk}, user={request.user}")
        return Response({'success': True, 'id': notif.id, 'is_read': notif.is_read})
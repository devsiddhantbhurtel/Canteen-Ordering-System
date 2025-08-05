from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, FoodItem, Order, OrderDetail, Feedback, Payment,PhoneVerification, Cart

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    contact_number = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'contact', 'contact_number', 'is_staff', 'is_superuser', 'is_active']

    def get_role(self, obj):
        try:
            profile = UserProfile.objects.get(user=obj)
            return profile.role.capitalize()
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=obj, role='student')
            return profile.role.capitalize()

    def get_contact(self, obj):
        try:
            profile = UserProfile.objects.get(user=obj)
            return profile.contact
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=obj, role='student')
            return profile.contact

    def get_contact_number(self, obj):
        try:
            profile = UserProfile.objects.get(user=obj)
            return profile.contact
        except UserProfile.DoesNotExist:
            return None

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = UserProfile
        fields = ['user', 'role']

import random
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, PhoneVerification  # Ensure you have imported PhoneVerification


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES, 
        default='student', 
        write_only=True
    )
    password = serializers.CharField(write_only=True)
    contact = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'contact']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already registered.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_contact(self, value):
        if UserProfile.objects.filter(contact=value).exists():
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value

    def create(self, validated_data):
        contact = validated_data.pop('contact')
        role = validated_data.pop('role')
        # Create the user
        user = User.objects.create_user(**validated_data)
        user.is_active = False  # Inactive until verified
        user.save()
        # Create the user profile storing role and contact
        UserProfile.objects.create(user=user, role=role, contact=contact)
        # Generate a random 4-digit OTP
        verification_code = str(random.randint(1000, 9999))
        PhoneVerification.objects.create(
            user=user,
            phone_number=contact,
            verification_code=verification_code,
            verified=False
        )
        # Send OTP via email (ensure your email settings are properly configured)
        from django.core.mail import send_mail
        send_mail(
            'Your Verification Code',
            f'Your OTP for registration is: {verification_code}',
            'no-reply@example.com',  # Update with your sender email
            [user.email],
            fail_silently=False,
        )
        # For testing, you can remove this print statement later.
        print(f"Verification code sent to {contact}: {verification_code}")
        return user

class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = '__all__'

class OrderDetailSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(read_only=True)
    food_item_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodItem.objects.all(),
        write_only=True,
        source='food_item'
    )
    subtotal = serializers.SerializerMethodField()
    food_item_name = serializers.CharField(read_only=True)
    food_item_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderDetail
        fields = ['id', 'food_item', 'food_item_id', 'food_item_name', 'food_item_price', 'quantity', 'customization', 'subtotal']
        
    def get_subtotal(self, obj):
        if obj.food_item:
            return float(obj.food_item.price * obj.quantity)
        elif obj.food_item_price:
            return float(obj.food_item_price * obj.quantity)
        return 0

class OrderSerializer(serializers.ModelSerializer):
    order_details = OrderDetailSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    customer_name = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'total_amount', 'payment_method', 'payment_status',
            'order_status', 'order_time', 'pickup_time', 'order_details', 
            'customer_name', 'formatted_date', 'items', 'is_offline'
        ]
        read_only_fields = ['user', 'total_amount', 'order_time']

    def get_customer_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None

    def get_formatted_date(self, obj):
        if obj.order_time:
            return obj.order_time.strftime("%b %d, %Y, %I:%M %p")
        return None

    def get_items(self, obj):
        items = []
        for detail in obj.order_details.all():
            # Defensive: handle deleted food_item
            if detail.food_item is not None:
                name = detail.food_item.name
                price = detail.food_item.price
            else:
                name = detail.food_item_name or "(deleted)"
                price = detail.food_item_price or 0
            items.append({
                'name': name,
                'price': price,
                'quantity': detail.quantity,
                'customization': detail.customization
            })
        return items

    def create(self, validated_data):
        order_details_data = self.context['request'].data.get('order_details', [])
        
        # Create order
        order = Order.objects.create(
            user=self.context['request'].user,
            payment_method=validated_data.get('payment_method', 'cod'),
            payment_status='pending',
            order_status='received',
            pickup_time=validated_data.get('pickup_time'),
            is_offline=validated_data.get('is_offline', True)
        )
        
        # Create order details and calculate total
        total_amount = 0
        for detail_data in order_details_data:
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
        
        # Update order
        order.save()
        
        return order

class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    food_item_name = serializers.CharField(source='food_item.name', read_only=True)
    food_item_image = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_date = serializers.DateTimeField(source='order.created_at', read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'user_name', 'food_item', 'food_item_name', 
                 'food_item_image', 'feedback_text', 'rating', 'created_at',
                 'order', 'order_id', 'order_date']
        read_only_fields = ['user', 'created_at', 'order_id', 'order_date']

    def get_food_item_image(self, obj):
        if obj.food_item and obj.food_item.image:
            return obj.food_item.image.url
        return None

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    rfid_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined', 'role', 'contact', 'rfid_id')
        read_only_fields = ('date_joined',)

    def get_role(self, obj):
        try:
            return obj.profile.role.capitalize()
        except (UserProfile.DoesNotExist, AttributeError):
            return 'Student'

    def get_contact(self, obj):
        try:
            return obj.profile.contact
        except (UserProfile.DoesNotExist, AttributeError):
            return None
            
    def get_rfid_id(self, obj):
        try:
            return obj.profile.rfid_id
        except (UserProfile.DoesNotExist, AttributeError):
            return None

class CartSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(read_only=True)
    food_item_id = serializers.PrimaryKeyRelatedField(
        source='food_item',
        queryset=FoodItem.objects.all(),
        write_only=True
    )
    total = serializers.SerializerMethodField()
    customization = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'food_item', 'food_item_id', 'quantity', 'customization', 'total']
        read_only_fields = ['user', 'total']

    def get_total(self, obj):
        return float(obj.food_item.price * obj.quantity)

    def validate(self, data):
        """
        Custom validation to ensure food_item exists and quantity is positive
        """
        food_item = data.get('food_item')
        quantity = data.get('quantity', 1)
        
        if not food_item:
            raise serializers.ValidationError({'food_item': 'Food item is required'})
            
        if quantity < 1:
            raise serializers.ValidationError({'quantity': 'Quantity must be at least 1'})
            
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        food_item = validated_data.get('food_item')
        quantity = validated_data.get('quantity', 1)
        customization = validated_data.get('customization', '')

        # Check if item already exists in cart with same customization
        cart_item, created = Cart.objects.get_or_create(
            user=user,
            food_item=food_item,
            customization=customization,
            defaults={'quantity': quantity}
        )

        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

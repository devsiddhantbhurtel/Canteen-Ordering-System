from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Extend the user model with a profile for role management
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    rfid_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    last_rfid_scan = models.DateTimeField(null=True, blank=True)
    contact = models.CharField(max_length=15, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reset_code = models.CharField(max_length=8, blank=True, null=True)
    reset_code_expiry = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

class FoodItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='food_images/', blank=True, null=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    PAYMENT_CHOICES = (
        ('khalti', 'Pay with Khalti'),
        ('cod', 'Cash on Delivery'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    )
    ORDER_STATUS_CHOICES = (
        ('received', 'Order Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    order_time = models.DateTimeField(auto_now_add=True)
    pickup_time = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='received')
    is_offline = models.BooleanField(default=False)

    @property
    def total_amount(self):
        return sum(detail.food_item.price * detail.quantity for detail in self.order_details.all())

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def process_payment(self):
        """Process the payment for this order"""
        if self.payment_status == 'pending':
            self.payment_status = 'completed'
            self.save()
            return True
        return False

    def complete_payment(self):
        """Complete the payment for this order"""
        if self.payment_status in ['pending', 'processing']:
            self.payment_status = 'completed'
            self.save()
            return True
        return False

    def cancel_payment(self):
        """Cancel the payment for this order"""
        if self.payment_status in ['pending', 'processing']:
            self.payment_status = 'failed'
            self.save()
            return True
        return False

    def process_order(self):
        """Move order to preparing state"""
        if self.order_status == 'received':
            self.order_status = 'preparing'
            self.save()
            return True
        return False

    def complete_order(self):
        """Complete the order"""
        if self.order_status == 'ready':
            self.order_status = 'completed'
            self.save()
            return True
        return False

    def cancel_order(self):
        """Cancel the order"""
        if self.order_status in ['received', 'preparing']:
            self.order_status = 'cancelled'
            self.save()
            return True
        return False

    def mark_ready(self):
        """Mark the order as ready for pickup"""
        if self.order_status == 'preparing':
            self.order_status = 'ready'
            self.save()
            return True
        return False

class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    food_item = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True, blank=True)
    food_item_name = models.CharField(max_length=255, blank=True, null=True)
    food_item_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    customization = models.TextField(blank=True, null=True)  # Customization added

    def __str__(self):
        return f"{self.quantity} of {self.food_item_name} - Customization: {self.customization}"

class Feedback(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, null=True)
    feedback_text = models.TextField(blank=True, null=True)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['order', 'food_item']

    def __str__(self):
        return f"Feedback for {self.food_item.name if self.food_item else 'Unknown'} by {self.user.username}"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=[
        ('COD', 'Cash on Delivery'),
        ('khalti', 'Khalti')
    ])
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ])
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    khalti_pidx = models.CharField(max_length=100, blank=True, null=True)
    khalti_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.method} - {self.status}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    customization = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.food_item.name} ({self.quantity})"

# Notification model for in-app notifications
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To: {self.recipient.username} - {self.message[:30]}..."


class PhoneVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='phone_verification')
    phone_number = models.CharField(max_length=15)
    verification_code = models.CharField(max_length=6)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Verification for {self.user.username}"

    class Meta:
        verbose_name = 'Phone Verification'
        verbose_name_plural = 'Phone Verifications'

from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = (
        ('received', 'Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('acknowledged', 'Acknowledged')
    )
    
    PRIORITY_CHOICES = (
        (1, 'High'),
        (2, 'Medium'),
        (3, 'Low')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_time = models.DateTimeField(auto_now_add=True)
    pickup_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    acknowledged = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # New fields for queue management
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    estimated_prep_time = models.IntegerField(default=15)  # in minutes
    queue_position = models.IntegerField(null=True, blank=True)
    started_preparing_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['pickup_time', 'priority', 'order_time']

    def calculate_priority(self):
        """Calculate priority based on pickup time and order complexity"""
        now = timezone.now()
        time_until_pickup = self.pickup_time - now
        
        # High priority if pickup time is less than 30 minutes away
        if time_until_pickup <= timedelta(minutes=30):
            return 1
        # Medium priority if pickup time is 30-60 minutes away
        elif time_until_pickup <= timedelta(minutes=60):
            return 2
        # Low priority for orders with pickup time more than 60 minutes away
        else:
            return 3

    def estimate_prep_time(self):
        """Estimate preparation time based on order items"""
        total_time = 0
        for detail in self.orderdetail_set.all():
            # Base time per item (5 minutes)
            item_time = 5
            # Add time based on quantity
            item_time += detail.quantity * 2
            # Add time for customization if any
            if detail.customization:
                item_time += 3
            total_time += item_time
        return total_time

    def should_start_preparing(self):
        """Determine if order should start preparing based on estimated prep time and pickup time"""
        if not self.pickup_time:
            return False
        
        now = timezone.now()
        time_until_pickup = self.pickup_time - now
        
        # Should start if time until pickup is less than or equal to estimated prep time + buffer
        buffer_time = 10  # 10 minutes buffer
        return time_until_pickup <= timedelta(minutes=self.estimated_prep_time + buffer_time)

    def save(self, *args, **kwargs):
        # Calculate priority if not set
        if not self.priority:
            self.priority = self.calculate_priority()
        
        # Calculate estimated prep time if not set
        if not self.estimated_prep_time:
            self.estimated_prep_time = self.estimate_prep_time()
        
        super().save(*args, **kwargs)

class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    food_item = models.ForeignKey('menu.FoodItem', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    customization = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.food_item.name} x{self.quantity}" 
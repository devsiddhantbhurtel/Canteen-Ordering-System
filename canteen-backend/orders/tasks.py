from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Order
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_order_queue():
    """
    Process the order queue automatically based on priority and timing
    """
    channel_layer = get_channel_layer()
    now = timezone.now()
    
    # Get all active orders (received or preparing)
    active_orders = Order.objects.filter(
        status__in=['received', 'preparing']
    ).order_by('pickup_time', 'priority', 'order_time')
    
    for order in active_orders:
        try:
            # If order should start preparing and is still in received status
            if order.should_start_preparing() and order.status == 'received':
                order.status = 'preparing'
                order.started_preparing_at = timezone.now()
                order.save()
                
                # Send WebSocket notification
                async_to_sync(channel_layer.group_send)(
                    f'order_{order.id}',
                    {
                        'type': 'order_status_update',
                        'message': {
                            'order': {
                                'id': order.id,
                                'status': 'preparing',
                                'started_preparing_at': order.started_preparing_at.isoformat()
                            }
                        }
                    }
                )
                
                logger.info(f"Order {order.id} automatically moved to preparing status")
            
            # If order is preparing and estimated prep time has passed
            elif (order.status == 'preparing' and 
                  order.started_preparing_at and 
                  now >= order.started_preparing_at + timedelta(minutes=order.estimated_prep_time)):
                order.status = 'ready'
                order.save()
                
                # Send WebSocket notification
                async_to_sync(channel_layer.group_send)(
                    f'order_{order.id}',
                    {
                        'type': 'order_status_update',
                        'message': {
                            'order': {
                                'id': order.id,
                                'status': 'ready'
                            }
                        }
                    }
                )
                
                logger.info(f"Order {order.id} automatically moved to ready status")
                
        except Exception as e:
            logger.error(f"Error processing order {order.id}: {str(e)}")

@shared_task
def update_order_priorities():
    """
    Periodically update order priorities based on pickup times
    """
    orders = Order.objects.filter(status__in=['received', 'preparing'])
    for order in orders:
        new_priority = order.calculate_priority()
        if new_priority != order.priority:
            order.priority = new_priority
            order.save()
            logger.info(f"Updated priority for order {order.id} to {new_priority}")

@shared_task
def cleanup_acknowledged_orders():
    """
    Archive or clean up old acknowledged orders
    """
    cutoff_time = timezone.now() - timedelta(days=1)
    old_orders = Order.objects.filter(
        status='acknowledged',
        order_time__lt=cutoff_time
    )
    old_orders.update(archived=True) 
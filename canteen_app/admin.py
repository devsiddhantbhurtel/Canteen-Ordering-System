from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, PhoneVerification, FoodItem, Order, Feedback, OrderDetail, Payment, Cart

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('role', 'rfid_id', 'contact', 'balance')
    
    def get_fields(self, request, obj=None):
        # Always show all fields, including rfid_id
        return ('role', 'rfid_id', 'contact', 'balance')

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_rfid')
    list_select_related = ('profile',)

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Role'

    def get_rfid(self, instance):
        return instance.profile.rfid_id
    get_rfid.short_description = 'RFID ID'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'rfid_id', 'contact', 'balance', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'rfid_id', 'contact')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'rfid_id', 'contact', 'balance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {
                'fields': ('user', 'role', 'rfid_id', 'contact', 'balance')
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PhoneVerification)
admin.site.register(FoodItem)
admin.site.register(Order)
admin.site.register(Feedback)
admin.site.register(OrderDetail)
admin.site.register(Payment)
admin.site.register(Cart)

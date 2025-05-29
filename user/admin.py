from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserType, CustomUser

@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ('email', 'user_type', 'is_active', 'is_staff', 'last_login')
    search_fields = ('email',)
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser')
    ordering = ('email',)
    readonly_fields = ('last_login',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('user_type',)}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        ('Important Dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_type', 'password1', 'password2'),
        }),
    )

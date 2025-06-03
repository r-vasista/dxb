from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from user.models import (
    UserType, CustomUser, Permission, Role
)

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
        (None, {'fields': ('email', 'password', 'full_name')}),
        ('Personal Info', {'fields': ('user_type',)}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'custom_permissions',
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


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'content_type', 'type']
    search_fields = ['code', 'content_type', 'type']
    list_filter = ['code', 'content_type', 'type']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'permissions'] 
    list_filter = ['name', 'permissions']
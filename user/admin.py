from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from user.models import (
    UserType, CustomUser, Permission, Role, UserLog, SocialAccount
)

@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ('id', 'email', 'user_type', 'is_active', 'is_staff', 'last_login', 'timezone', 'provider')
    search_fields = ('email',)
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser')
    ordering = ('-id',)
    readonly_fields = ('last_login',)

    fieldsets = (
        (None, {'fields': ('email', 'password', 'full_name', 'roles', 'timezone','provider')}),
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
    list_display = ['id', 'code', 'content_type', 'type', 'scope']
    search_fields = ['code', 'content_type', 'type', 'scope']
    list_filter = ['code', 'content_type', 'type', 'scope']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name', 'permissions'] 
    list_filter = ['name', 'permissions']


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'login_time', 'timezone']
    search_fields = ['id', 'user', 'login_time', 'timezone']
    list_filter = ['id', 'user', 'login_time', 'timezone']


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'provider', 'email']
    search_fields = ['id', 'user', 'provider', 'email']
    list_filter = ['id', 'user', 'provider', 'email']

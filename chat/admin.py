from django.contrib import admin
from chat.models import (
    ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt, ChatClear, ScheduleMessage, ChatGroupTheme, ChatTheme
)

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'type']
    search_fields =  ['id', 'group', 'type']
    list_filter = ['id', 'group', 'type']
    
@admin.register(ChatGroupMember)
class ChatGroupMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'profile']
    search_fields =  ['id', 'group', 'profile']
    list_filter = ['id', 'group', 'profile']
    
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'sender']
    search_fields =  ['id', 'group', 'sender']
    list_filter = ['id', 'group', 'sender']

@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'is_seen']
    search_fields =  ['id', 'message', 'user', 'is_seen']
    list_filter = ['id', 'message', 'user', 'is_seen']


@admin.register(ChatClear)
class ChatClearAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'group', 'cleared_at']
    search_fields =  ['id', 'profile', 'group', 'cleared_at']
    list_filter = ['id', 'profile', 'group', 'cleared_at']

@admin.register(ScheduleMessage)
class ScheduleMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'group', 'scheduled_at', 'executed']
    search_fields = ['id', 'sender', 'group', 'scheduled_at', 'executed']
    list_filter = ['id', 'sender', 'group', 'scheduled_at', 'executed']
    
@admin.register(ChatGroupTheme)
class ChatGroupThemeAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'theme', 'applied_by', 'applied_at']
    search_fields = ['id', 'group', 'theme', 'applied_by', 'applied_at']
    list_filter = ['id', 'group', 'theme', 'applied_by', 'applied_at']
    
@admin.register(ChatTheme)
class ChatThemeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'background_image', 'type', 'uploaded_by', 'is_public']
    search_fields =  ['id', 'name', 'type', 'uploaded_by', 'is_public']
    list_filter = ['id', 'name', 'type', 'uploaded_by', 'is_public']

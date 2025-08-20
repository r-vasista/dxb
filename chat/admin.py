from django.contrib import admin
from chat.models import (
    ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt
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

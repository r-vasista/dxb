from django.contrib import admin
    
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupJoinRequest
)

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'creator']
    search_fields =  ['id', 'name', 'creator']
    list_filter = ['id', 'name', 'creator']
    
@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'profile', 'role']
    search_fields =  ['id', 'group', 'profile', 'role']
    list_filter = ['id', 'group', 'profile', 'role']

@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'profile', 'content']
    search_fields =  ['id', 'group', 'profile', 'content']
    list_filter = ['id', 'group', 'profile', 'content']


@admin.register(GroupJoinRequest)
class GroupJoinRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'profile', 'status']
    search_fields =  ['id', 'group', 'profile', 'status']
    list_filter = ['id', 'group', 'profile', 'status']

    
    
@admin.register(GroupPostComment)
class GroupPostCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'group_post', 'profile', 'content']
    search_fields =  ['id', 'group_post', 'profile', 'content']
    list_filter = ['id', 'group_post', 'profile', 'content']

@admin.register(GroupPostLike)
class GroupPostLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'group_post', 'profile']
    search_fields =  ['id', 'group_post', 'profile']
    list_filter = ['id', 'group_post', 'profile', ]


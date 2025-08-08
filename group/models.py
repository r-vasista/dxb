from django.db import models

# Local imports
from group.choices import (
    RoleChoices, GroupType, PrivacyChoices, JoiningRequestStatus
)
from profiles.models import (
    Profile
)
from core.models import (
    HashTag, BaseModel
)

class Group(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=GroupType.choices, default=GroupType.GROUP)
    description = models.TextField(max_length=500)
    tags = models.ManyToManyField(HashTag, related_name='groups', blank=True)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_groups')
    privacy = models.CharField(max_length=20, choices=PrivacyChoices.choices, default=PrivacyChoices.PUBLIC)
    logo = models.ImageField(upload_to='group_logo/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='group_covers/', null=True, blank=True)
    member_count = models.PositiveIntegerField(default=1)
    post_count = models.PositiveIntegerField(default=0)
    avg_engagement = models.FloatField(default=0.0)  # avg reactions + comments per post
    trending_score = models.FloatField(default=0.0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    featured = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    

class GroupMember(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    joined_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='assigned_roles', blank=True, null=True)
    is_banned = models.BooleanField(default=False)
    top_contributor = models.BooleanField(default=False)
    recent_activity_score = models.IntegerField(default=0)

    class Meta:
        unique_together = ('profile', 'group')
        
    def __str__(self):
        return f'{self.group.name}, {self.profile}'


class GroupPost(BaseModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    content = models.TextField()
    media_file = models.FileField(upload_to='group_media/', null=True, blank=True)
    tags = models.ManyToManyField(HashTag, blank=True)
    is_pinned = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    is_flagged = models.BooleanField(default=False)
    flag_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f'{self.group.name}, {self.id}'


class GroupPostComment(BaseModel):
    """
    Comments on group posts
    """
    group_post = models.ForeignKey(GroupPost, on_delete=models.CASCADE, related_name='comments')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    like_count = models.IntegerField(default=0)
    
    # Comment content
    content = models.TextField()
        
    def __str__(self):
        return f"Comment by {self.profile.username} on {self.group_post.group.name} post"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def reply_count(self):
        return self.replies.filter(is_active=True).count()


class GroupPostLike(BaseModel):
    group_post = models.ForeignKey(GroupPost, on_delete=models.CASCADE, related_name='post_likes')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group_post', 'profile'], name='unique_group_post_like')
        ]

    def __str__(self):
        return f"{self.profile.username} liked post in {self.group_post.group.name}"


class GroupPostCommentLike(BaseModel):
    """
    Likes on group post comments
    """
    comment = models.ForeignKey(GroupPostComment, on_delete=models.CASCADE, related_name='comment_likes')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment', 'profile'], name='unique_group_post_comment_like')
        ]

    def __str__(self):
        return f"{self.profile.username} liked comment by {self.comment.profile.username}"


class GroupJoinRequest(BaseModel):
    """
    Model to handle join requests for groups.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="group_join_requests")
    status = models.CharField(max_length=20, choices=JoiningRequestStatus, default=JoiningRequestStatus.PENDING)
    message = models.TextField(blank=True)

    class Meta:
        unique_together = ('group', 'profile')

    def __str__(self):
        return f"{self.profile.username} → {self.group.name} ({self.status})"

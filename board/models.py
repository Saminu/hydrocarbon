import os

from hashlib import sha224

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    nick = models.CharField(max_length=16)

    def __str__(self):
        return self.nick


class OneTimeUser(models.Model):
    nick = models.CharField(max_length=16)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.nick


class Board(models.Model):
    name = models.CharField(max_length=16)
    slug = models.SlugField()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('board_post_list', kwargs={'board': self.slug})


class Category(models.Model):
    board = models.ForeignKey('Board', related_name='categories')
    name = models.CharField(max_length=8)
    slug = models.SlugField()

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=16)

    def __str__(self):
        return self.name


class VotableModelMixin:
    @property
    def votes(self):
        vd = dict()
        vd['upvote'] = self._votes.filter(vote=Vote.UPVOTE).count()
        vd['downvote'] = self._votes.filter(vote=Vote.DOWNVOTE).count()
        vd['total'] = vd['upvote'] - vd['downvote']
        return vd


class AuthorModelMixin:
    @property
    def author(self):
        if self.user:
            return self.user.profile.nick
        else:
            return self.onetime_user.nick

    @property
    def iphash(self):
        return sha224(self.ipaddress.encode()).hexdigest()[:10]


class Post(AuthorModelMixin, VotableModelMixin, models.Model):
    user = models.ForeignKey(User, blank=True, null=True, related_name='posts')
    onetime_user = models.OneToOneField('OneTimeUser', blank=True, null=True, related_name='post', on_delete=models.SET_NULL)
    ipaddress = models.GenericIPAddressField(protocol='IPv4')
    board = models.ForeignKey('Board', related_name='posts')
    category = models.ForeignKey('Category', blank=True, null=True, related_name='posts')
    title = models.CharField(max_length=32)
    contents = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    viewcount = models.PositiveIntegerField(default=0)
    created_time = models.DateTimeField(auto_now_add=True)
    modified_time = models.DateTimeField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'pk': self.id})

    def save(self, *args, **kwargs):
        if not kwargs.pop('auto_now', False):
            self.modified_time = timezone.now()
        super(Post, self).save(*args, **kwargs)


class Comment(AuthorModelMixin, VotableModelMixin, models.Model):
    post = models.ForeignKey('Post', related_name='comments')
    comment = models.ForeignKey('self', related_name='subcomments', blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True, related_name='comments')
    onetime_user = models.OneToOneField('OneTimeUser', blank=True, null=True, related_name='comment', on_delete=models.SET_NULL)
    ipaddress = models.GenericIPAddressField(protocol='IPv4')
    contents = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)


class Vote(models.Model):
    DOWNVOTE = -1
    UPVOTE = 1
    VOTE_CHOICES = (
        (DOWNVOTE, 'Not recommend'),
        (UPVOTE, 'Recommend'),
    )
    post = models.ForeignKey('Post', blank=True, null=True, related_name='_votes')
    comment = models.ForeignKey('Comment', blank=True, null=True, related_name='_votes')
    user = models.ForeignKey(User, blank=True, null=True, related_name='_votes')
    ipaddress = models.GenericIPAddressField(protocol='IPv4')
    vote = models.SmallIntegerField(choices=VOTE_CHOICES)


class Announcement(models.Model):
    post = models.OneToOneField('Post', related_name='announcement')
    boards = models.ManyToManyField('Board', related_name='announcements')


def upload_to_func(instance, filename):
    checksum = instance.checksum
    return os.path.join(checksum[0], checksum[:2], checksum)

class Attachment(models.Model):
    post = models.ForeignKey('Post', blank=True, null=True, related_name='attachments')
    name = models.CharField(max_length=64)
    file = models.FileField(upload_to=upload_to_func)
    content_type = models.CharField(max_length=64)
    checksum = models.CharField(max_length=64)
    dlcount = models.PositiveIntegerField(default=0)

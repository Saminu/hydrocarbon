from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from account.models import EmailAddress
from account.views import LoginView, SettingsView, SignupView
from haystack.query import SearchQuerySet
from redactor.views import RedactorUploadView

from board.forms import CommentForm, HCLoginForm, HCSignupForm, HCSettingsForm, PostForm
from board.mixins import AjaxMixin, BoardURLMixin, BPostListMixin, PostListMixin, PermissionCheckMixin, UserFormMixin, UserURLMixin
from board.models import Board, Category, Comment, OneTimeUser, Post, Tag, User, Vote
from board.utils import is_empty_html, normalize


class IndexView(View):
    def get(self, request, *args, **kwargs):
        board = Board.objects.first()
        return redirect(reverse('board_post_list', kwargs={'board': board.slug}))


class HCLoginView(LoginView):
    form_class = HCLoginForm

    def login_user(self, form):
        email = EmailAddress.objects.get_primary(form.user)
        if not email.verified:
            self.request.session['redirect_to'] = settings.ACCOUNT_LOGIN_URL
            messages.error(self.request, _('Please confirm email.'))
        else:
            acd = form.user.accountdeletion_set
            if acd.exists():
                acd.all().delete()
                messages.success(self.request, _('Account restored.'))
            super().login_user(form)


class HCSignupView(SignupView):
    form_class = HCSignupForm

    def create_user(self, form, commit=True, **kwargs):
        user = get_user_model()(**kwargs)
        user.email = form.cleaned_data['email'].strip()
        user.nickname = form.cleaned_data['nickname'].strip()
        password = form.cleaned_data.get('password')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class HCSettingsView(SettingsView):
    form_class = HCSettingsForm

    def get_initial(self):
        initial = super().get_initial()
        initial['nickname'] = self.request.user.nickname
        return initial

    def update_settings(self, form):
        self.update_email(form)
        self.update_nickname(form)

    def update_nickname(self, form):
        user = self.request.user
        user.nickname = form.cleaned_data['nickname']
        user.save()


class HCRedactorUploadView(RedactorUploadView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return FormView.dispatch(self, request, *args, **kwargs)


class UserProfileView(UserURLMixin, DetailView):
    model = User
    context_object_name = 'u'
    template_name = 'user/profile.html'

    def get_object(self, queryset=None):
        return self.user


class UserPostListView(UserURLMixin, PostListMixin, ListView):
    template_name = 'user/post_list.html'

    def get_base_queryset(self):
        return self.user.posts


class UserCommentListView(UserURLMixin, ListView):
    template_name = 'user/comment_list.html'
    paginate_by = 10

    def get_queryset(self):
        return self.user.comments.all()


class PostCreateView(BoardURLMixin, UserFormMixin, CreateView):
    model = Post
    form_class = PostForm

    def get_success_url(self):
        qdict = QueryDict('', mutable=True)
        qdict.update({
            'type': 'p',
            'target': str(self.object.id),
            'vote': '++',
        })
        r = self.request
        r.POST = qdict
        v = VoteAjaxView()
        v.post(r)
        return super().get_success_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['board'] = self.board
        kwargs['show_ot_form'] = not self.request.user.is_authenticated()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not self.request.user.is_authenticated():
            ot_user = self.request.session.get('onetime_user')
            if ot_user:
                initial['onetime_nick'] = ot_user.get('nick')
                initial['onetime_password'] = ot_user.get('password')
        return initial


class PostUpdateView(PermissionCheckMixin, UpdateView):
    model = Post
    form_class = PostForm

    def get(self, request, *args, **kwargs):
        if (not kwargs.pop('authenticated', False)) and self.object.user is None:
            self.show_password_form()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('password'):
            if self.check_permission():
                kwargs['authenticated'] = True
            request.method = 'GET'
            return self.get(request, *args, **kwargs)
        else:
            return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['board'] = self.object.board
        return kwargs

    def get_success_url(self):
        Tag.objects.filter(posts=None).delete()
        return super().get_success_url()


class PostDeleteView(PermissionCheckMixin, DeleteView):
    model = Post

    def get(self, request, *args, **kwargs):
        if self.object.user is None:
            self.show_password_form()
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if not self.check_permission():
            return self.get(request, *args, **kwargs)
        if self.object.onetime_user is not None:
            self.object.onetime_user.delete()
        r = super().delete(request, *args, **kwargs)
        Tag.objects.filter(posts=None).delete()
        return r

    def get_success_url(self):
        messages.success(self.request, _('Deleted'))
        return reverse('board_post_list', kwargs={'board': self.object.board.slug})


class BaseBPostListView(BoardURLMixin, BPostListMixin, ListView):
    pass


class PostListView(BaseBPostListView):
    pass


class PostBestListView(BaseBPostListView):
    def queryset_post_filter(self, queryset):
        pqs = queryset.filter(vote__gte=settings.BOARD_POST_BEST_VOTES)
        return pqs

    def get_context_data(self, **kwargs):
        kwargs['best'] = True
        return super().get_context_data(**kwargs)


class PostListByCategoryView(BaseBPostListView):
    template_name = 'board/postlist/by_category.html'

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, slug=kwargs.get('category'))
        return super().dispatch(request, *args, **kwargs)

    def queryset_post_filter(self, queryset):
        pqs = queryset.filter(category=self.category)
        return pqs

    def get_context_data(self, **kwargs):
        kwargs['category'] = self.category
        return super().get_context_data(**kwargs)


class BoardSearchView(BaseBPostListView):
    def queryset_post_filter(self, queryset):
        self.q = self.request.GET.get('q')
        sqs = SearchQuerySet().models(Post)
        sqs = sqs.filter(board=self.board.slug, content=self.q)
        pqs = queryset.filter(pk__in=[s.pk for s in sqs])
        return pqs

    def get_context_data(self, **kwargs):
        kwargs['search'] = {'query': self.q}
        return super().get_context_data(**kwargs)


class PostListByTagView(PostListMixin, ListView):
    template_name = 'board/postlist/by_tag.html'

    def dispatch(self, request, *args, **kwargs):
        self.tag = get_object_or_404(Tag, name=kwargs.get('tag'))
        return super().dispatch(request, *args, **kwargs)

    def get_base_queryset(self):
        pqs = Post.objects.filter(tags=self.tag, announcement=None)
        return pqs

    def get_context_data(self, **kwargs):
        kwargs['tag'] = self.tag
        return super().get_context_data(**kwargs)


class PostDetailView(DetailView):
    model = Post

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        self.board = post.board
        post_ids_viewed = self.request.session.get('post_ids_viewed', list())
        if post.id not in post_ids_viewed:
            post.viewcount += 1
            post.save(auto_now=False)
            post_ids_viewed.append(post.id)
            self.request.session['post_ids_viewed'] = post_ids_viewed
        return post

    def get_context_data(self, **kwargs):
        request = self.request
        referer = self.request.META.get('HTTP_REFERER')
        p = urlparse(referer)
        request.GET = QueryDict(p.query)
        plv = PostListView()
        plv.kwargs = dict()
        plv.request = request
        plv.dispatch(request, board=self.board.slug, is_detailview=True)
        ctx = plv.get_context_data()
        kwargs.update(ctx)
        kwargs['board'] = self.board
        voted = {'upvoted': False, 'downvoted': False}
        if self.request.user.is_authenticated():
            vqs = self.object._votes.filter(user=self.request.user)
        else:
            vqs = self.object._votes.filter(user=None, ipaddress=self.request.META['REMOTE_ADDR'])
        if vqs.exists():
            vote = vqs.first()
            if vote.vote == Vote.UPVOTE:
                voted['upvoted'] = True
            elif vote.vote == Vote.DOWNVOTE:
                voted['downvoted'] = True
        kwargs['voted'] = voted
        f = CommentForm(show_ot_form=True)
        if not self.request.user.is_authenticated():
            ot_user = self.request.session.get('onetime_user')
            if ot_user:
                f.initial = {'onetime_nick': ot_user.get('nick'), 'onetime_password': ot_user.get('password')}
        kwargs['comment_form'] = f
        return super().get_context_data(**kwargs)


class VoteAjaxView(AjaxMixin, View):
    def post(self, request):
        target_type = request.POST.get('type')
        target_id = request.POST.get('target', '')
        vote = request.POST.get('vote')
        vote_dicts = request.session.get('vote_dicts', list())

        if ((target_type not in ('p', 'c')) or
                (not target_id.isdigit()) or
                (vote not in ('++', '-+', '+-', '--'))):
            return self.bad_request()
        target_id = int(target_id)

        vote_dict = {'type': target_type, 'id': target_id, 'vote': vote}
        if vote_dict in vote_dicts:
            return JsonResponse({'status': 'alreadyhave'}, status=409)

        if target_type == 'p':
            try:
                post = Post.objects.get(id=target_id)
            except Post.DoesNotExist:
                return self.bad_request()
            vqs = Vote.objects.filter(post=post)
        else:
            try:
                comment = Comment.objects.get(id=target_id)
            except Comment.DoesNotExist:
                return self.bad_request()
            vqs = Vote.objects.filter(comment=comment)
        if request.user.is_authenticated():
            vqs = vqs.filter(user=request.user)
        else:
            vqs = vqs.filter(user=None, ipaddress=request.META['REMOTE_ADDR'])

        if vote[0] == '+':
            if vote[1] == '-' and not request.user.is_authenticated():
                return JsonResponse({'status': 'notauthenticated'}, status=401)
            if vqs.exists():
                return JsonResponse({'status': 'alreadyhave'}, status=409)
            v = Vote()
            if target_type == 'p':
                v.post = post
            else:
                v.comment = comment
            if vote[1] == '+':
                v.vote = Vote.UPVOTE
            else:
                v.vote = Vote.DOWNVOTE
            if request.user.is_authenticated():
                v.user = request.user
            v.ipaddress = request.META['REMOTE_ADDR']
            v.save()
            vote_dicts.append(vote_dict)
            request.session['vote_dicts'] = vote_dicts
            return JsonResponse({'status': 'success', 'current': post.votes if target_type == 'p' else comment.votes})
        else:
            if vote[1] == '+':
                vqs = vqs.filter(vote=Vote.UPVOTE)
            else:
                vqs = vqs.filter(vote=Vote.DOWNVOTE)
            if not vqs.exists():
                return self.not_found()
            v = vqs.first()
            v.delete()
            vote_dict['vote'] = '+' + vote[1]
            if vote_dict in vote_dicts:
                vote_dicts.remove(vote_dict)
                request.session['vote_dicts'] = vote_dicts
            return JsonResponse({'status': 'success', 'current': post.votes if target_type == 'p' else comment.votes})


class CommentAjaxView(AjaxMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.pk = kwargs.pop('pk')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            post = Post.objects.get(pk=self.pk)
        except Post.DoesNotExist:
            return self.not_found()

        def _make_list(comments):
            lst = list()
            comments = comments.order_by('created_time')
            for comment in comments:
                subcomments = None
                if comment.subcomments.exists():
                    subcomments = _make_list(comment.subcomments.filter(comment=comment))
                voted = {'upvoted': False, 'downvoted': False}
                if request.user.is_authenticated():
                    vqs = comment._votes.filter(user=request.user)
                else:
                    vqs = comment._votes.filter(user=None, ipaddress=request.META['REMOTE_ADDR'])
                if vqs.exists():
                    vote = vqs.first()
                    if vote.vote == Vote.UPVOTE:
                        voted['upvoted'] = True
                    elif vote.vote == Vote.DOWNVOTE:
                        voted['downvoted'] = True
                lst.append({
                    'id': comment.id,
                    'author': comment.author,
                    'author_total_score': comment.user.total_score if comment.user else None,
                    'author_url': comment.user.get_absolute_url() if comment.user else None,
                    'iphash': comment.iphash if not comment.user else None,
                    'contents': comment.contents,
                    'created_time': comment.created_time,
                    'votes': comment.votes,
                    'voted': voted,
                    'subcomments': subcomments,
                })
            lst.sort(key=lambda c: c['votes']['total'], reverse=True)
            return lst
        lst = _make_list(post.comments.filter(comment=None))
        return JsonResponse({'status': 'success', 'comments': {'count': post.comments.count(), 'list': lst}})

    def post(self, request, *args, **kwargs):
        target_type = request.POST.get('type')
        c = Comment()
        if target_type == 'p':
            try:
                c.post = Post.objects.get(pk=self.pk)
            except Post.DoesNotExist:
                return self.not_found()
        elif target_type == 'c':
            try:
                c.comment = Comment.objects.get(pk=self.pk)
                c.post = c.comment.post
                if c.depth > settings.BOARD_COMMENT_MAX_DEPTH:
                    return self.bad_request()
            except Comment.DoesNotExist:
                return self.not_found()
        else:
            return self.bad_request()
        contents = request.POST.get('contents')
        if is_empty_html(contents):
            return JsonResponse({'status': 'badrequest', 'error_fields': ['contents']}, status=400)
        if request.user.is_authenticated():
            c.user = request.user
        else:
            ot_user = OneTimeUser()
            ot_user.nick = request.POST.get('ot_nick')
            ot_user.password = request.POST.get('ot_password')
            request.session['onetime_user'] = {'nick': ot_user.nick, 'password': ot_user.password}
            try:
                ot_user.full_clean()
            except ValidationError as ex:
                return JsonResponse({'status': 'badrequest', 'error_fields': list(ex.message_dict.keys())}, status=400)
            else:
                ot_user.password = make_password(ot_user.password)
                ot_user.save()
                c.onetime_user = ot_user
        c.ipaddress = request.META['REMOTE_ADDR']
        c.contents = request.POST.get('contents')
        c.save()
        qdict = QueryDict('', mutable=True)
        qdict.update({
            'type': 'c',
            'target': str(c.id),
            'vote': '++',
        })
        r = request
        r.POST = qdict
        v = VoteAjaxView()
        v.post(r)
        return self.success()

    def put(self, request, *args, **kwargs):
        try:
            c = Comment.objects.get(pk=self.pk)
        except Comment.DoesNotExist:
            return self.not_found()
        if c.user:
            if (not request.user.is_staff) and (c.user != request.user):
                return self.permission_denied()
        else:
            if (not request.user.is_staff) and not check_password(request.META.get('HTTP_X_HC_PASSWORD'), c.onetime_user.password):
                return self.permission_denied()
        PUT = QueryDict(request.body)
        contents = PUT.get('contents')
        if is_empty_html(contents):
            return JsonResponse({'status': 'badrequest', 'error_fields': ['contents']}, status=400)
        c.contents = contents
        c.save()
        return self.success()

    def delete(self, request, *args, **kwargs):
        try:
            c = Comment.objects.get(pk=self.pk)
        except Comment.DoesNotExist:
            return self.not_found()
        if c.user:
            if (not request.user.is_staff) and (c.user != request.user):
                return self.permission_denied()
        else:
            if (not request.user.is_staff) and not check_password(request.META.get('HTTP_X_HC_PASSWORD'), c.onetime_user.password):
                return self.permission_denied()
            c.onetime_user.delete()
        c.delete()
        return self.success()


class TagAutocompleteAjaxView(AjaxMixin, View):
    def post(self, request, *args, **kwargs):
        query = request.POST.get('query')
        if not query:
            return self.bad_request()
        sqs = SearchQuerySet()
        sqs = sqs.models(Tag).filter(content__exact=normalize(query))
        lst = [{'value': sr.object.name, 'data': sr.object.posts.count()} for sr in sqs.all()]
        return JsonResponse({'status': 'success', 'query': query, 'suggestions': lst})


class JSConstantsView(TemplateView):
    template_name = 'constants.js'
    content_type = 'application/javascript'

    def get(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs['BOARD_COMMENT_BLIND_VOTES'] = settings.BOARD_COMMENT_BLIND_VOTES
        kwargs['BOARD_COMMENT_MAX_DEPTH'] = settings.BOARD_COMMENT_MAX_DEPTH
        return super().get_context_data(**kwargs)

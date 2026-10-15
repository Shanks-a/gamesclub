"""Game-scoped community content and deterministic, order-backed leaderboards."""
import io
import uuid
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Value, BooleanField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import CommunityPost, CommunityImage, CommunityLike, CommunityComment, GamePartition, Order, Partner
from .views import err, get_idem, save_idem

PAGE_SIZE = 20
VISIBLE_AUTHOR = Q(author__is_active=True) & (Q(author__profile__is_enabled=True) | Q(author__profile__isnull=True))


def author_data(user):
    profile = getattr(user, 'profile', None)
    return {'id': user.id, 'nickname': profile.nickname if profile else '玩家',
            'avatar_url': profile.avatar_url if profile else ''}


def visible_posts():
    return CommunityPost.objects.filter(VISIBLE_AUTHOR, is_hidden=False, game__is_enabled=True)


def posts_query(user):
    liked = Exists(CommunityLike.objects.filter(post_id=OuterRef('pk'), user_id=user.id)) if user.is_authenticated else Value(False, output_field=BooleanField())
    return visible_posts().select_related('author__profile').prefetch_related('images').annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', filter=Q(comments__is_hidden=False, comments__author__is_active=True) &
                            (Q(comments__author__profile__is_enabled=True) | Q(comments__author__profile__isnull=True)), distinct=True),
        liked=liked,
    )


def post_data(post, user):
    return {'id': post.id, 'game_id': post.game_id, 'author': author_data(post.author),
            'content': post.content, 'created_at': post.created_at.isoformat(),
            'images': [{'id': image.id, 'url': image.image.url} for image in post.images.all()],
            'like_count': post.like_count, 'comment_count': post.comment_count, 'liked': post.liked,
            'can_delete': user.is_authenticated and post.author_id == user.id}


def comment_data(comment, user):
    return {'id': comment.id, 'author': author_data(comment.author), 'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'can_delete': user.is_authenticated and comment.author_id == user.id}


class PostInput(serializers.Serializer):
    content = serializers.CharField(max_length=1000, allow_blank=True, default='')
    image_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=9, default=list)

    def validate(self, attrs):
        if not attrs['content'] and not attrs['image_ids']:
            raise serializers.ValidationError('请填写动态内容或添加图片')
        if len(set(attrs['image_ids'])) != len(attrs['image_ids']):
            raise serializers.ValidationError('图片不能重复')
        return attrs


class CommentInput(serializers.Serializer):
    content = serializers.CharField(max_length=300, allow_blank=False)


def cursor_value(request, key):
    raw = request.query_params.get(key, '0')
    if not raw.isascii() or not raw.isdigit() or len(raw) > 12:
        raise serializers.ValidationError({key: '分页参数无效'})
    return int(raw)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def game_posts(request, game_id):
    game = get_object_or_404(GamePartition, pk=game_id, is_enabled=True)
    if request.method == 'GET':
        before = cursor_value(request, 'before')
        query = posts_query(request.user).filter(game=game)
        if before:
            query = query.filter(id__lt=before)
        rows = list(query.order_by('-id')[:PAGE_SIZE + 1])
        return Response({'results': [post_data(post, request.user) for post in rows[:PAGE_SIZE]],
                         'next_before': rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None})
    form = PostInput(data=request.data)
    form.is_valid(raise_exception=True)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'COMMUNITY_POST')
        if replay is not None:
            return replay
        # Recheck the partition while publishing, including a concurrent disable.
        get_object_or_404(GamePartition.objects.select_for_update(), pk=game_id, is_enabled=True)
        image_ids = form.validated_data['image_ids']
        images = list(CommunityImage.objects.select_for_update().filter(id__in=image_ids, uploader=request.user, post__isnull=True))
        if len(images) != len(image_ids):
            return err('图片不可用，请重新上传', 'INVALID_COMMUNITY_IMAGE')
        post = CommunityPost.objects.create(game=game, author=request.user, content=form.validated_data['content'])
        for image in images:
            image.post = post
            image.position = image_ids.index(image.id)
        CommunityImage.objects.bulk_update(images, ['post', 'position'])
        result = Response(post_data(posts_query(request.user).get(pk=post.pk), request.user), status=201)
        save_idem(request.user, state, 'COMMUNITY_POST', post.id, result)
        return result


@api_view(['DELETE'])
def delete_post(request, pk):
    with transaction.atomic():
        post = get_object_or_404(CommunityPost.objects.select_for_update(), pk=pk, author=request.user)
        post.is_hidden = True
        post.save(update_fields=['is_hidden'])
    return Response(status=204)


@api_view(['PUT'])
def post_like(request, pk):
    liked = request.data.get('liked')
    if type(liked) is not bool:
        return err('请指定点赞状态', 'INVALID_LIKE')
    with transaction.atomic():
        get_object_or_404(visible_posts().select_for_update(of=('self',)), pk=pk)
        if liked:
            CommunityLike.objects.get_or_create(post_id=pk, user=request.user)
        else:
            CommunityLike.objects.filter(post_id=pk, user=request.user).delete()
        return Response({'liked': liked, 'like_count': CommunityLike.objects.filter(post_id=pk).count()})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_comments(request, pk):
    post = get_object_or_404(visible_posts(), pk=pk)
    if request.method == 'GET':
        after = cursor_value(request, 'after')
        query = post.comments.filter(VISIBLE_AUTHOR, is_hidden=False, id__gt=after).select_related('author__profile')
        rows = list(query.order_by('id')[:PAGE_SIZE + 1])
        return Response({'results': [comment_data(comment, request.user) for comment in rows[:PAGE_SIZE]],
                         'next_after': rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None})
    form = CommentInput(data=request.data)
    form.is_valid(raise_exception=True)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'COMMUNITY_COMMENT')
        if replay is not None:
            return replay
        get_object_or_404(visible_posts().select_for_update(of=('self',)), pk=pk)
        comment = CommunityComment.objects.create(post=post, author=request.user, **form.validated_data)
        result = Response(comment_data(comment, request.user), status=201)
        save_idem(request.user, state, 'COMMUNITY_COMMENT', comment.id, result)
        return result


@api_view(['DELETE'])
def delete_comment(request, pk):
    comment = get_object_or_404(CommunityComment, pk=pk, author=request.user)
    comment.is_hidden = True
    comment.save(update_fields=['is_hidden'])
    return Response(status=204)


@api_view(['POST'])
def upload_image(request):
    file = request.FILES.get('file')
    if not file or file.size > 5 * 1024 * 1024:
        return err('请选择不超过5MB的图片', 'INVALID_IMAGE')
    try:
        with Image.open(file) as picture:
            if picture.format not in ('JPEG', 'PNG', 'WEBP') or picture.width * picture.height > 20_000_000:
                raise ValueError()
            picture = ImageOps.exif_transpose(picture).convert('RGB')
            picture.thumbnail((2048, 2048))
            output = io.BytesIO()
            picture.save(output, format='JPEG', quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return err('仅支持有效的 JPEG、PNG、WebP 图片', 'INVALID_IMAGE')
    image = CommunityImage(uploader=request.user)
    image.image.save(uuid.uuid4().hex + '.jpg', ContentFile(output.getvalue()), save=False)
    try:
        image.save()
    except Exception:
        image.image.delete(save=False)
        raise
    return Response({'id': image.id, 'url': image.image.url}, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def leaderboard(request, game_id):
    get_object_or_404(GamePartition, pk=game_id, is_enabled=True)
    sort = request.query_params.get('sort', 'heat')
    if sort not in ('heat', 'orders'):
        return err('榜单排序无效', 'INVALID_SORT')
    offset = cursor_value(request, 'offset')
    now = timezone.now()
    completed = Q(orders__status=Order.Status.COMPLETED, orders__product__game_id=game_id)
    recent = completed & Q(orders__completed_at__gte=now - timedelta(days=30), orders__completed_at__lte=now)
    query = Partner.objects.filter(game_id=game_id, is_active=True, user__is_active=True).filter(
        Q(user__profile__is_enabled=True) | Q(user__profile__isnull=True),
    ).select_related('user__profile').annotate(
        completed_orders=Count('orders', filter=completed), recent_orders=Count('orders', filter=recent),
    ).order_by(*(['-recent_orders', '-completed_orders', 'id'] if sort == 'heat' else ['-completed_orders', '-recent_orders', 'id']))

    def entry(partner, rank):
        return {'id': partner.id, 'rank': rank, **{key: value for key, value in author_data(partner.user).items() if key != 'id'},
                'intro': partner.intro, 'completed_orders': partner.completed_orders, 'recent_orders': partner.recent_orders}

    count = query.count()
    rows = list(query[offset:offset + PAGE_SIZE])
    return Response({'sort': sort, 'generated_at': now.isoformat(), 'count': count,
                     'top_three': [entry(partner, index + 1) for index, partner in enumerate(query[:3])],
                     'results': [entry(partner, offset + index + 1) for index, partner in enumerate(rows)],
                     'next_offset': offset + PAGE_SIZE if offset + PAGE_SIZE < count else None})

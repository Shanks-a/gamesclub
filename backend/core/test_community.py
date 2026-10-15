import io
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from .models import (AccessToken, CommunityPost, CommunityComment, CommunityImage, CommunityLike,
                     GamePartition, Order, Partner, Product, ProductCategory, UserProfile)


class CommunityTests(APITestCase):
    def setUp(self):
        self.game = GamePartition.objects.create(name='王者荣耀')
        self.other_game = GamePartition.objects.create(name='和平精英')
        self.author = self.user('author')
        self.other = self.user('other')
        self.auth(self.author)
        self.post_url = f'/api/v1/games/{self.game.id}/posts/'

    def user(self, name):
        user = get_user_model().objects.create_user(username=name)
        UserProfile.objects.create(user=user, nickname=name)
        return user

    def auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)

    def publish(self, content='今天也要快乐开黑', key='post-1', **extra):
        return self.client.post(self.post_url, {'content':content, **extra}, format='json', HTTP_IDEMPOTENCY_KEY=key)

    def test_public_feed_is_game_scoped_and_requires_auth_for_write(self):
        post = self.publish().data
        CommunityPost.objects.create(game=self.other_game, author=self.other, content='another game')
        self.client.credentials()
        response = self.client.get(self.post_url)
        self.assertEqual([row['id'] for row in response.data['results']], [post['id']])
        self.assertFalse(response.data['results'][0]['can_delete'])
        self.assertEqual(self.publish(key='anonymous').status_code, 401)
        self.assertEqual(self.client.post(f"/api/v1/community/posts/{post['id']}/comments/", {'content':'test'}).status_code, 401)

    def test_publish_is_idempotent_and_content_cannot_impersonate_author(self):
        first = self.publish(author=self.other.id)
        second = self.publish(author=self.other.id)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(first.data['author']['id'], self.author.id)
        self.assertEqual(CommunityPost.objects.count(), 1)
        self.assertEqual(self.publish(content='changed', author=self.other.id).status_code, 409)
        self.assertEqual(self.publish(content='  ', key='blank').status_code, 400)
        self.assertEqual(self.publish(content='a'*1001, key='large').status_code, 400)
        self.assertEqual(self.publish(image_ids=[1]*10, key='many').status_code, 400)

    def test_cursor_pagination_is_stable_when_new_posts_arrive(self):
        CommunityPost.objects.bulk_create([CommunityPost(game=self.game, author=self.author, content=str(i)) for i in range(25)])
        first = self.client.get(self.post_url).data
        self.publish(key='new')
        second = self.client.get(self.post_url, {'before':first['next_before']}).data
        self.assertEqual(len(first['results']), 20)
        self.assertEqual(len(second['results']), 5)
        self.assertFalse(set(row['id'] for row in first['results']) & set(row['id'] for row in second['results']))
        self.assertEqual(self.client.get(self.post_url, {'before':'bad'}).status_code, 400)

    def test_likes_are_set_operations_and_counts_do_not_multiply_with_comments(self):
        post = self.publish().data
        url = f"/api/v1/community/posts/{post['id']}/like/"
        self.assertEqual(self.client.put(url, {'liked':True}, format='json').data['like_count'], 1)
        self.assertEqual(self.client.put(url, {'liked':True}, format='json').data['like_count'], 1)
        self.auth(self.other)
        self.client.put(url, {'liked':True}, format='json')
        CommunityComment.objects.bulk_create([CommunityComment(post_id=post['id'], author=self.other, content='good') for _ in range(3)])
        row = self.client.get(self.post_url).data['results'][0]
        self.assertEqual((row['like_count'], row['comment_count'], row['liked']), (2,3,True))
        self.assertEqual(self.client.put(url, {'liked':False}, format='json').data['like_count'], 1)
        self.assertEqual(self.client.put(url, {'liked':'yes'}, format='json').status_code, 400)
        self.assertEqual(CommunityLike.objects.count(), 1)

    def test_comments_persist_retry_once_and_enforce_ownership(self):
        post = self.publish().data
        url = f"/api/v1/community/posts/{post['id']}/comments/"
        response = self.client.post(url, {'content':'  好配合  '}, format='json', HTTP_IDEMPOTENCY_KEY='comment-1')
        repeated = self.client.post(url, {'content':'  好配合  '}, format='json', HTTP_IDEMPOTENCY_KEY='comment-1')
        self.assertEqual(response.data['id'], repeated.data['id'])
        self.assertEqual(response.data['content'], '好配合')
        self.assertEqual(self.client.post(url, {'content':'  '}, format='json', HTTP_IDEMPOTENCY_KEY='blank-comment').status_code, 400)
        delete_url = f"/api/v1/community/comments/{response.data['id']}/"
        self.auth(self.other)
        self.assertEqual(self.client.delete(delete_url).status_code, 404)
        self.auth(self.author)
        self.assertEqual(self.client.delete(delete_url).status_code, 204)
        self.assertEqual(self.client.get(url).data['results'], [])
        self.assertEqual(CommunityComment.objects.count(), 1)

    def test_hidden_and_disabled_content_cannot_be_read_or_interacted_with(self):
        post = self.publish().data
        post_url = f"/api/v1/community/posts/{post['id']}/"
        self.auth(self.other)
        self.assertEqual(self.client.delete(post_url).status_code, 404)
        self.auth(self.author)
        self.assertEqual(self.client.delete(post_url).status_code, 204)
        self.assertEqual(self.client.get(self.post_url).data['results'], [])
        self.assertEqual(self.client.put(post_url+'like/', {'liked':True}, format='json').status_code, 404)
        self.assertEqual(self.client.get(post_url+'comments/').status_code, 404)
        self.assertTrue(CommunityPost.objects.get(pk=post['id']).is_hidden)
        self.game.is_enabled=False; self.game.save()
        self.assertEqual(self.publish(key='disabled-game').status_code, 404)

    def test_disabled_author_is_not_public(self):
        self.publish()
        self.author.profile.is_enabled=False; self.author.profile.save()
        self.client.credentials()
        self.assertEqual(self.client.get(self.post_url).data['results'], [])

    def test_images_are_validated_reencoded_and_owned(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            invalid = SimpleUploadedFile('bad.jpg', b'not an image', content_type='image/jpeg')
            self.assertEqual(self.client.post('/api/v1/community/images/', {'file':invalid}).status_code, 400)
            stream = io.BytesIO(); Image.new('RGB', (8,8), 'blue').save(stream, format='PNG')
            upload = self.client.post('/api/v1/community/images/', {'file':SimpleUploadedFile('test.png',stream.getvalue(),content_type='image/png')})
            self.assertEqual(upload.status_code, 201)
            image_id = upload.data['id']
            self.auth(self.other)
            self.assertEqual(self.publish(key='stolen', image_ids=[image_id]).status_code, 400)
            self.auth(self.author)
            self.assertEqual(self.publish(key='duplicate', image_ids=[image_id,image_id]).status_code, 400)
            post = self.publish(content='', key='with-image', image_ids=[image_id])
            self.assertEqual(post.status_code, 201)
            self.assertTrue(post.data['images'][0]['url'].endswith('.jpg'))
            self.assertEqual(CommunityImage.objects.get(pk=image_id).post_id, post.data['id'])
            self.assertEqual(self.publish(key='reused', image_ids=[image_id]).status_code, 400)

    def test_comment_pagination(self):
        post = self.publish().data
        CommunityComment.objects.bulk_create([CommunityComment(post_id=post['id'], author=self.author, content=str(i)) for i in range(23)])
        url = f"/api/v1/community/posts/{post['id']}/comments/"
        first = self.client.get(url).data
        last = self.client.get(url, {'after':first['next_after']}).data
        self.assertEqual((len(first['results']),len(last['results'])), (20,3))
        self.assertIsNone(last['next_after'])


class LeaderboardTests(APITestCase):
    def setUp(self):
        self.game = GamePartition.objects.create(name='Rank game')
        self.other = GamePartition.objects.create(name='Other game')
        self.customer = get_user_model().objects.create_user(username='customer')
        category = ProductCategory.objects.create(game=self.game, name='Category')
        self.product = Product.objects.create(game=self.game, category=category, title='Product', price_cents=100, original_price_cents=100)
        other_category = ProductCategory.objects.create(game=self.other, name='Category')
        self.other_product = Product.objects.create(game=self.other, category=other_category, title='Other', price_cents=100, original_price_cents=100)
        self.now = timezone.now()
        self.url = f'/api/v1/games/{self.game.id}/leaderboard/'
        self.order_number = 0

    def partner(self, name, game=None, active=True):
        user = get_user_model().objects.create_user(username=name)
        UserProfile.objects.create(user=user, nickname=name)
        return Partner.objects.create(user=user, game=game or self.game, is_active=active)

    def order(self, partner, age=0, status=Order.Status.COMPLETED, product=None):
        self.order_number += 1
        return Order.objects.create(order_no=f'RANK-{self.order_number}', user=self.customer, product=product or self.product,
                                    partner=partner, quantity=1, unit_price_cents=100, total_amount_cents=100,
                                    game_name_snapshot='game', product_title_snapshot='Product',
                                    completed_at=self.now-timedelta(days=age), status=status)

    def test_heat_and_total_rank_by_correct_game_status_and_window(self):
        old = self.partner('old'); hot = self.partner('hot'); empty = self.partner('empty')
        for _ in range(4): self.order(old, age=31)
        self.order(hot, age=30); self.order(hot, age=0)
        self.order(empty, status=Order.Status.CANCELLED)
        self.order(empty, status=Order.Status.IN_SERVICE)
        self.order(empty, product=self.other_product)
        self.order(empty, age=-1)  # Future timestamps never count as recent activity.
        self.partner('other-partner', game=self.other)
        self.partner('disabled', active=False)
        disabled_user = self.partner('disabled-user'); disabled_user.user.profile.is_enabled=False; disabled_user.user.profile.save()
        with patch('core.community_api.timezone.now', return_value=self.now):
            heat = self.client.get(self.url).data
            total = self.client.get(self.url, {'sort':'orders'}).data
        self.assertEqual([row['id'] for row in heat['results']], [hot.id, old.id, empty.id])
        self.assertEqual([row['id'] for row in total['results']], [old.id, hot.id, empty.id])
        self.assertEqual(heat['results'][0]['recent_orders'], 2)
        self.assertEqual(heat['results'][2]['recent_orders'], 0)
        self.assertEqual([row['rank'] for row in heat['top_three']], [1,2,3])
        self.assertEqual(heat['count'], 3)

    def test_rank_pagination_and_equal_scores_are_deterministic(self):
        partners = [self.partner(f'p{i}') for i in range(23)]
        first = self.client.get(self.url).data
        last = self.client.get(self.url, {'offset':first['next_offset']}).data
        self.assertEqual([row['id'] for row in first['results']], [partner.id for partner in partners[:20]])
        self.assertEqual([row['rank'] for row in last['results']], [21,22,23])
        self.assertEqual(first['top_three'],last['top_three'])
        self.assertEqual(self.client.get(self.url, {'sort':'random'}).status_code,400)
        self.assertEqual(self.client.get(self.url, {'offset':'-1'}).status_code,400)

    def test_empty_or_disabled_partition(self):
        self.assertEqual(self.client.get(self.url).data['top_three'], [])
        self.game.is_enabled=False; self.game.save()
        self.assertEqual(self.client.get(self.url).status_code,404)

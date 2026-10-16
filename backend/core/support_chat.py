"""Private customer/partner support threads. Staff share a team inbox/read state."""
from django.db import transaction
from django.db.models import Q, Count, Max
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .management_api import endpoint
from .models import Order, SupportConversation, SupportMessage


class SendSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000, trim_whitespace=True)
    client_key = serializers.UUIDField()


class OpenSerializer(serializers.Serializer):
    order_no = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    recipient = serializers.ChoiceField(choices=['customer', 'partner'], default='customer')


def message_data(message):
    return {'id': message.id, 'content': message.content, 'from_staff': message.from_staff,
            'sender_name': message.sender.get_username() if message.from_staff else '',
            'read_at': message.read_at, 'created_at': message.created_at}


def thread_data(thread, staff, messages):
    last = messages[-1] if messages else None
    profile = getattr(thread.user, 'profile', None)
    is_partner = (thread.order.partner_id and thread.order.partner.user_id == thread.user_id) if thread.order_id else hasattr(thread.user, 'partner')
    return {'id': thread.id, 'user': thread.user_id,
            'name': (profile.nickname if profile else '') or thread.user.get_username(),
            'order_no': thread.order.order_no if thread.order_id else '',
            'role': '陪玩' if is_partner else '用户',
            'updated_at': thread.updated_at,
            'unread_count': getattr(thread, 'unread_total', sum(m.from_staff != staff and m.read_at is None for m in messages)),
            'reply_state': ('needs_reply' if last.from_staff != staff else 'awaiting_reply') if last else 'empty',
            'last_message': message_data(last) if last else None}


def handle(request, pk=None, staff=False):
    qs = SupportConversation.objects.select_related('user__profile', 'user__partner', 'order__partner')
    if not staff:
        qs = qs.filter(user=request.user)
    if pk is None:
        if request.method == 'GET':
            threads = list(qs.annotate(
                unread_total=Count('messages', filter=Q(messages__from_staff=not staff, messages__read_at__isnull=True)),
                last_id=Max('messages__id')).order_by('-updated_at', '-id'))
            latest = {m.id: m for m in SupportMessage.objects.filter(id__in=[t.last_id for t in threads if t.last_id]).select_related('sender')}
            return Response([thread_data(t, staff, [latest[t.last_id]] if t.last_id else []) for t in threads])
        data = OpenSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        number = data.validated_data['order_no']
        order, user = None, request.user
        if number:
            orders = Order.objects.select_related('partner__user')
            if not staff:
                orders = orders.filter(Q(user=request.user) | Q(partner__user=request.user))
            order = orders.filter(order_no=number).first()
            if order is None:
                return Response({'error': {'message': '订单不存在'}}, status=404)
            if staff:
                if data.validated_data['recipient'] == 'partner':
                    if not order.partner_id:
                        return Response({'error': {'message': '订单尚未分配实际陪玩'}}, status=409)
                    user = order.partner.user
                else:
                    user = order.user
        elif staff:
            return Response({'error': {'message': '请选择需要联系的订单和参与者'}}, status=400)
        thread, _ = SupportConversation.objects.get_or_create(
            user=user, context_key=str(order.id) if order else 'general', defaults={'order': order})
        return Response({'id': thread.id})

    thread = qs.filter(pk=pk).first()
    if thread is None:
        return Response({'error': {'message': '会话不存在'}}, status=404)
    if request.method == 'GET':
        messages = list(thread.messages.select_related('sender'))
        unread = {m.id for m in messages if m.from_staff != staff and m.read_at is None}
        now = timezone.now()
        SupportMessage.objects.filter(id__in=unread, read_at__isnull=True).update(read_at=now)
        for m in messages:
            if m.id in unread:
                m.read_at = now
        return Response({**thread_data(thread, staff, messages), 'messages': [message_data(m) for m in messages]})
    data = SendSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    with transaction.atomic():
        # Serialize sends and retries so equal retries cannot duplicate or change text.
        thread = SupportConversation.objects.select_for_update().get(pk=thread.id)
        message, created = SupportMessage.objects.get_or_create(
            conversation=thread, sender=request.user, client_key=data.validated_data['client_key'],
            defaults={'content': data.validated_data['content'], 'from_staff': staff})
        if message.content != data.validated_data['content']:
            return Response({'error': {'message': '重试标识已用于其他消息，请重新发送'}}, status=409)
        if created:
            thread.save(update_fields=['updated_at'])
        return Response(message_data(message), status=201 if created else 200)


@api_view(['GET', 'POST'])
def customer_threads(request, pk=None):
    return handle(request, pk)


@endpoint(['GET', 'POST'])
def staff_threads(request, pk=None):
    return handle(request, pk, staff=True)

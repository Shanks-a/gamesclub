"""Order participants drive service progress; caller owns the transaction."""
from django.utils import timezone

from .models import AuditLog, Conversation, Message, Order, OrderStatusHistory
from .staff_orders import WorkflowError


def partner_progress(actor, pk, data, action):
    if not isinstance(data, dict) or set(data) != {'version'} or type(data.get('version')) is not int:
        raise WorkflowError('请刷新订单后操作', 'VERSION_REQUIRED', 400)
    order = Order.objects.select_for_update(of=('self',)).filter(pk=pk, partner__user=actor).first()
    if order is None:
        raise WorkflowError('订单不存在或不是你的接单订单', 'NOT_FOUND', 404)
    if order.user_id == actor.pk:
        raise WorkflowError('不能为自己的下单订单提供服务', 'SELF_SERVICE', 403)
    if order.version != data['version']:
        raise WorkflowError('订单已更新，请刷新后重试', 'VERSION_CONFLICT')
    if order.payment_status != Order.PaymentStatus.PAID:
        raise WorkflowError('订单尚未付款', 'ORDER_UNPAID')
    source, target, kind, content = {
        'start': (Order.Status.ACCEPTED, Order.Status.IN_SERVICE,
                  Message.Kind.SERVICE_STARTED, '陪玩已开始服务。'),
        'complete': (Order.Status.IN_SERVICE, Order.Status.PENDING_CONFIRMATION,
                     Message.Kind.COMPLETION_REQUEST, '陪玩申请完成服务，请下单用户核实后确认；确认前订单仍为待验收。'),
    }[action]
    if order.status != source:
        raise WorkflowError('当前订单状态不能执行此操作', 'ORDER_STATE_CONFLICT')
    conversation = Conversation.objects.filter(order=order, user_id=order.user_id, partner_id=order.partner_id).first()
    if conversation is None:
        raise WorkflowError('订单会话不一致，请联系客服核查', 'CONVERSATION_CONFLICT')
    before = {'status': order.status, 'version': order.version}
    timestamp_field = 'started_at' if action == 'start' else 'completion_requested_at'
    setattr(order, timestamp_field, timezone.now())
    order.status = target
    order.version += 1
    order.save(update_fields=['status', 'version', timestamp_field, 'updated_at'])
    Message.objects.create(conversation=conversation, sender=Message.Sender.PARTNER, kind=kind, content=content)
    OrderStatusHistory.objects.create(order=order, from_status=source, to_status=target, actor=actor, action='PARTNER_' + action.upper())
    AuditLog.objects.create(actor=actor, action='partner_' + action, resource='order', resource_id=str(pk),
                            before=before, after={'status': target, 'version': order.version})
    return order

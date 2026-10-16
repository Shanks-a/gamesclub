"""Customer-service assignment; callers must use a transaction."""
from rest_framework.exceptions import APIException

from .models import Order, Partner, Conversation, OrderStatusHistory, AuditLog


class WorkflowError(APIException):
    def __init__(self, message, code, status=409):
        self.status_code = status
        super().__init__({'error': {'message': message, 'code': code}})


def change_order(actor, pk, data, action):
    if action != 'assign':
        raise WorkflowError('请由实际接单陪玩在订单会话中操作服务进度', 'PARTNER_MANAGED_SERVICE', 403)
    allowed = {'version', 'partner_id', 'note'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise WorkflowError('请求字段无效', 'INVALID_FIELDS', 400)
    if type(data.get('version')) is not int:
        raise WorkflowError('请刷新订单后操作', 'VERSION_REQUIRED', 400)
    note = data.get('note', '')
    if not isinstance(note, str) or len(note) > 500:
        raise WorkflowError('处理说明不能超过500字', 'INVALID_NOTE', 400)
    order = Order.objects.select_for_update().filter(pk=pk).first()
    if not order:
        raise WorkflowError('订单不存在', 'NOT_FOUND', 404)
    if order.version != data['version']:
        raise WorkflowError('订单已更新，请刷新后重试', 'VERSION_CONFLICT')
    if order.payment_status != Order.PaymentStatus.PAID:
        raise WorkflowError('订单尚未付款', 'ORDER_UNPAID')
    source = (Order.Status.PENDING_ARRANGEMENT, Order.Status.PENDING_ACCEPTANCE)
    target = Order.Status.ACCEPTED
    if order.status not in source:
        raise WorkflowError('当前订单状态不能执行此操作', 'ORDER_STATE_CONFLICT')
    before = {'status': order.status, 'partner_id': order.partner_id, 'version': order.version}
    partner_id = data.get('partner_id')
    if type(partner_id) is not int:
        raise WorkflowError('请选择实际接单陪玩', 'INVALID_PARTNER', 400)
    partner = Partner.objects.select_for_update().filter(pk=partner_id).first()
    if not partner:
        raise WorkflowError('陪玩不存在', 'NOT_FOUND', 404)
    profile = getattr(partner.user, 'profile', None)
    if not partner.is_active or not partner.user.is_active or (profile and not profile.is_enabled):
        raise WorkflowError('该陪玩已暂停接单或账号被停用', 'PARTNER_DISABLED')
    if partner.game_id != order.product.game_id:
        raise WorkflowError('陪玩必须属于订单游戏分区', 'PARTNER_GAME_MISMATCH')
    if partner.user_id == order.user_id:
        raise WorkflowError('不能将订单派给下单用户本人', 'SELF_SERVICE', 400)
    if order.preferred_partner_id and order.preferred_partner_id != partner.id and not note.strip():
        raise WorkflowError('请先与客户协商更换人选并填写处理说明', 'CHANGE_REASON_REQUIRED', 400)
    if order.appointment_date and order.appointment_slot:
        conflict = Order.objects.filter(
            partner=partner, appointment_date=order.appointment_date,
            appointment_slot=order.appointment_slot,
        ).exclude(status__in=[Order.Status.CANCELLED, Order.Status.COMPLETED]).exclude(pk=pk).exists()
        if conflict:
            raise WorkflowError('该陪玩在该时段已有未完成订单', 'PARTNER_CONFLICT')
    # Never rebind an existing conversation: it may contain private messages.
    conversation = Conversation.objects.filter(order=order).first()
    if conversation and (conversation.partner_id != partner.id or conversation.user_id != order.user_id):
        raise WorkflowError('已有会话参与者不一致，请核查订单', 'CONVERSATION_CONFLICT')
    order.partner = partner
    Conversation.objects.get_or_create(order=order, defaults={'user_id': order.user_id, 'partner': partner})
    order.status = target
    order.version += 1
    order.save(update_fields=['partner', 'status', 'version', 'updated_at'])
    OrderStatusHistory.objects.create(
        order=order, from_status=before['status'], to_status=target,
        action='STAFF_' + action.upper(), actor=actor,
    )
    AuditLog.objects.create(
        actor=actor, action='staff_' + action, resource='order', resource_id=str(pk),
        before=before, after={'status': target, 'partner_id': order.partner_id,
                              'version': order.version, 'note': note.strip()},
    )
    return order

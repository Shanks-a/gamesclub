"""Public contact configuration contains no credentials or customer data."""
import re
from rest_framework import serializers
from .models import SystemConfig


class SupportConfigSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['disabled', 'wechat', 'enterprise'])
    corp_id = serializers.CharField(max_length=64, allow_blank=True, default='')
    url = serializers.CharField(max_length=300, allow_blank=True, default='')
    notice = serializers.CharField(max_length=200, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['mode'] == 'enterprise':
            if not re.fullmatch(r'[a-zA-Z0-9_-]{3,64}', attrs['corp_id']):
                raise serializers.ValidationError('请填写有效企业 ID')
            if not re.fullmatch(r'https://work\.weixin\.qq\.com/kfid/[a-zA-Z0-9_-]+', attrs['url']):
                raise serializers.ValidationError('请填写 https://work.weixin.qq.com/kfid/ 开头的企业微信客服链接')
        else:
            attrs['corp_id'] = ''
            attrs['url'] = ''
        return attrs


def get_support_config():
    value = SystemConfig.objects.filter(key='customer_support').values_list('value_json', flat=True).first()
    serializer = SupportConfigSerializer(data=value or {'mode': 'disabled'})
    if serializer.is_valid():
        return dict(serializer.validated_data)
    return {'mode': 'disabled', 'corp_id': '', 'url': '', 'notice': ''}

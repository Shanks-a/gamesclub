"""微信小程序登录：调用 code2session 换取 openid/session_key。

安全约定：
- AppSecret 仅存于后端环境变量（backend/.env），绝不进入前端、日志或响应体。
- 本模块对外只暴露 errcode 与可安全展示的错误文案，不泄露 openid/session_key 原始值。
- 一次性使用：code 由微信保证 5 分钟有效且换过后即失效，服务端不缓存 session_key。
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger('core.wechat')

WECHAT_CODESESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'


class WechatLoginError(Exception):
    """微信登录失败。errcode 为微信返回的错误码，message 为可安全展示给用户的文案。"""

    def __init__(self, errcode, message):
        self.errcode = errcode
        self.message = message
        super().__init__(f'wechat code2session error {errcode}: {message}')


# 可安全展示给用户的 errcode → 文案映射（不暴露技术细节与 openid）。
_SAFE_MESSAGES = {
    40029: '登录凭证无效或已过期，请重新登录',
    40013: '小程序配置无效，请联系客服',
    40163: '登录凭证已使用，请重新登录',
    40226: '当前账号存在风险，无法登录',
    45011: '登录过于频繁，请稍后再试',
    41008: '缺少登录凭证',
    -1: '微信服务繁忙，请稍后重试',
}


def code2session(code):
    """用一次性 code 换取 openid/session_key/unionid。

    返回 dict：{openid, session_key, unionid(可选)}。
    网络或微信返回异常时抛出 WechatLoginError。
    """
    appid = settings.WECHAT_APPID
    secret = settings.WECHAT_APPSECRET
    if not appid or not secret:
        raise WechatLoginError(-2, '微信登录未配置，请联系管理员')

    params = urllib.parse.urlencode({
        'appid': appid,
        'secret': secret,
        'js_code': code,
        'grant_type': 'authorization_code',
    })
    url = f'{WECHAT_CODESESSION_URL}?{params}'
    req = urllib.request.Request(url)

    try:
        # 依赖系统代理（本机 http://127.0.0.1:12450），urllib 默认读环境变量。
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        logger.warning('wechat code2session http error %s', e.code)
        raise WechatLoginError(-1, _SAFE_MESSAGES[-1])
    except urllib.error.URLError as e:
        logger.warning('wechat code2session network error: %s', e.reason)
        raise WechatLoginError(-1, _SAFE_MESSAGES[-1])

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning('wechat code2session non-json response')
        raise WechatLoginError(-1, _SAFE_MESSAGES[-1])

    errcode = data.get('errcode')
    if errcode:
        # 仅记录 errcode，不记录任何可能包含敏感信息的原始响应。
        logger.warning('wechat code2session errcode=%s', errcode)
        raise WechatLoginError(errcode, _SAFE_MESSAGES.get(errcode, '登录失败，请稍后重试'))

    if not data.get('openid'):
        logger.warning('wechat code2session missing openid')
        raise WechatLoginError(-1, _SAFE_MESSAGES[-1])

    return {
        'openid': data['openid'],
        'session_key': data.get('session_key', ''),
        'unionid': data.get('unionid', ''),
    }

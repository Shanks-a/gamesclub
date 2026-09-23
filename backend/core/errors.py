import logging
import time
import uuid
from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail=response.data
        response.data={'error':{'code':str(response.status_code),'message':str(detail.get('detail','参数不正确')) if isinstance(detail,dict) else '请求失败','details':detail}}
    return response

class RequestLogMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        start=time.monotonic(); request_id=uuid.uuid4().hex
        response=self.get_response(request)
        response['X-Request-ID']=request_id
        logging.getLogger('django.request').info('%s %s %s %s %.3fs',request_id,request.method,request.path,response.status_code,time.monotonic()-start)
        return response

from rest_framework.renderers import JSONRenderer

class UTF8JSONRenderer(JSONRenderer):
    media_type = 'application/json'
    charset = 'utf-8'

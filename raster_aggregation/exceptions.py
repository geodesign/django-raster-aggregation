from rest_framework.exceptions import APIException


class MissingQueryParameter(APIException):
    status_code = 500
    default_detail = 'Missing Query Parameter.'

from rest_framework import serializers
from . import models
import re
from django.utils.timezone import make_naive

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

class LibrarySerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Library
        fields = '__all__'
    
    def validate_key(self, v):
        if not _SLUG_RE.match(v):
            raise serializers.ValidationError("key must be lowercase letters, digits, or underscore only")
        return v

class SignalSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Signal
        fields = '__all__'

class ForecastSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Forecast
        fields = '__all__'
        read_only_fields = ['created_at']
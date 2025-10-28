from django.db import models

# Create your models here.
class Library(models.Model):
    key             = models.CharField(max_length=32, unique=True)
    name            = models.CharField(max_length=150, unique=True)

class Signal(models.Model):
    library         = models.ForeignKey(Library, on_delete=models.CASCADE)
    ts              = models.DateTimeField(db_index=True)
    wifi_clients    = models.IntegerField()
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "ts"],
                name = "uniq_signal_per_library_ts"
            )
        ]

class Forecast(models.Model):
    library         = models.ForeignKey(Library, on_delete=models.CASCADE)
    ts              = models.DateTimeField(db_index=True)
    horizon_min     = models.IntegerField()
    occupancy_pred  = models.FloatField()
    model_version   = models.CharField(max_length=64)
    model_family    = models.CharField(max_length=32, default="cnn_lstm_attn")
    created_at      = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ["library", "ts", "horizon_min", "model_version", "model_family"],
                name = "uniq_forecast_per_lib_ts_hz_ver_family"
            )
        ]


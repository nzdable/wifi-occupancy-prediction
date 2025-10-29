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

# occupancy/models.py

class ModelCandidate(models.Model):
    """
    A trained/servable model *family+version* available for a library.
    Example: family='cnn_lstm_attn', version='v1'.
    One row per (library, family, version).
    """
    FAMILY_CHOICES = [
        ("cnn", "cnn"),
        ("lstm", "lstm"),
        ("cnn_lstm", "cnn_lstm"),
        ("cnn_lstm_attn", "cnn_lstm_attn"),
    ]

    library       = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="candidates")
    family        = models.CharField(max_length=32, choices=FAMILY_CHOICES)
    version       = models.CharField(max_length=64, default="v1")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "family", "version"],
                name="uniq_candidate_per_library_family_version"
            )
        ]


class ModelEvaluation(models.Model):
    """
    Stores evaluation metrics for a candidate on that library (computed offline or via an admin action).
    Keep only the last N; one row per evaluation run (so you can compare over time).
    """
    candidate     = models.ForeignKey(ModelCandidate, on_delete=models.CASCADE, related_name="evaluations")
    evaluated_at  = models.DateTimeField(auto_now_add=True)
    r2            = models.FloatField(null=True)
    mse           = models.FloatField(null=True)
    rmse          = models.FloatField(null=True)
    notes         = models.TextField(blank=True, default="")

class ActiveModel(models.Model):
    """
    One row per library pointing to the currently selected candidate.
    Admins can switch this, or an auto-selection job can update it.
    """
    library       = models.OneToOneField(Library, on_delete=models.CASCADE, related_name="active_model")
    candidate     = models.ForeignKey(ModelCandidate, on_delete=models.PROTECT)

    # Optional: store how/why this was chosen
    selected_at   = models.DateTimeField(auto_now=True)
    selected_by   = models.CharField(max_length=128, blank=True, default="manual")  # or "auto"
    criterion     = models.CharField(max_length=64, blank=True, default="rmse_min")

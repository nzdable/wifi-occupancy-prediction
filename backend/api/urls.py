from django.urls import path
from . import views

urlpatterns = [ 
    path("health/", views.health, name="health-check"),
    path("debug/predict", views.predict_debug, name = "predict_debug"),
    path("forecast/debug", views.DebugSeedView.as_view())
]

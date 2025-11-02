from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_uploads
from . import views_forecast

router = DefaultRouter()
router.register(r"libraries", views.LibraryViewSet, basename="library")
router.register(r"signals", views.SignalViewSet, basename="views")
router.register(r"forecasts", views.ForecastViewSet, basename = "forecasts")
router.register(r"candidates", views.ModelCandidateViewSet, basename="candidate")
router.register(r"active", views.ActiveModelViewSet, basename="active-model")

urlpatterns = [
    path("", include(router.urls)),
    path("uploads/cleaned-wifi/", views_uploads.CleanedWifiCsvUploadView.as_view()),
    path("forecast/at", views_forecast.ForecastAtView.as_view()),
    path("forecast/day", views_forecast.ForecastDayView.as_view()),
    path("history/day", views_forecast.HistoryDayView.as_view()),
]

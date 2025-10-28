from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_uploads

router = DefaultRouter()
router.register(r"libraries", views.LibraryViewSet, basename="library")
router.register(r"signals", views.SignalViewSet, basename="views")
router.register(r"forecasts", views.ForecastViewSet, basename = "forecasts")

urlpatterns = [
    path("", include(router.urls)),
    path("uploads/cleaned-wifi", views_uploads.CleanedWifiCsvUploadView.as_view()),
]

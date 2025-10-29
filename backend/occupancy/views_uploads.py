from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from .permissions import IsAdminOrReadOnly
from .models import Library, Signal
from .ingest import aggregate_per_cleaned_library
from typing import List

class CleanedWifiCsvUploadView(APIView):
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        lib_key = request.data.get("library")
        if not lib_key:
            return Response({"detail": "Missing 'library'."}, status=400)

        try:
            lib = Library.objects.get(key=lib_key)
        except Library.DoesNotExist:
            return Response({"detail": f"Unknown library '{lib_key}'."}, status=404)

        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Missing file."}, status=400)

        tz = request.data.get("tz", "Asia/Manila")
        ts_col = request.data.get("ts_col", "Start_dt")
        mac_col = request.data.get("mac_col", "Client MAC")
        dayfirst = str(request.data.get("dayfirst", "true")).lower() in ("true", "1", "yes")

        try:
            df = pd.read_csv(f)
            agg = aggregate_per_cleaned_library(df, tz=tz, ts_col=ts_col, mac_col=mac_col, dayfirst=dayfirst)
        except Exception as e:
            return Response({"detail": f"Parse/aggregate error: {e}"}, status=400)

        rows: List[Signal] = [
            Signal(
                library=lib,
                ts=(ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts),  # pandas -> py datetime
                wifi_clients=int(count),                                           # numpy int -> py int
            )
            for (ts, count) in agg.itertuples(index=False, name=None)
        ]
        Signal.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)


        return Response({"ok": True, "rows_ingested": len(rows)}, status=201)

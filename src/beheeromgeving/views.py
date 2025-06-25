from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import DataContract, DataTeam
from .serializers import DataContractSerializer, DataTeamSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "OK"})


class DataTeamViewSet(ModelViewSet):
    queryset = DataTeam.objects.all()
    serializer_class = DataTeamSerializer


class DataContractViewSet(ModelViewSet):
    queryset = DataContract.objects.all()
    serializer_class = DataContractSerializer

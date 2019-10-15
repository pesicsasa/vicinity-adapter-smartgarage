from django.urls import path

from . import views

urlpatterns = [
    path('access/logs', views.AccessLogs.as_view(), name='access_logs'),
    # path('test', views.TestPage.as_view(), name='test'),
    path('objects', views.ObjectsView.as_view(), name='objects_view'),
    path('reservations/property/<pid>', views.ParkingReservationView.as_view(), name='parking_reservation_view_dash'),
    path('objects/<iid>/publishers/<oid>/events/<eid>', views.EventHandler.as_view(), name='event_handler'),
]
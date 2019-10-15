from django.db import models
from django.utils.translation import ugettext_lazy as _

# Create your models here.


class ParkingReservation(models.Model):
    name = models.CharField(_('name'), max_length=256)
    email = models.CharField(_('email'), max_length=256)
    valid_from = models.DateTimeField(_('valid_from'))
    valid_until = models.DateTimeField(_('valid_until'))
    payment_id = models.CharField(_('payment_id'), max_length=256)
    payment_address = models.CharField(_('payment_address'), max_length=256)
    amount = models.DecimalField(_('amount'), decimal_places=8, max_digits=1000)
    request_origin = models.CharField(_('request_origin'), max_length=256)
    payment_status = models.CharField(_('payment_status'), max_length=256)
    voucher_generated = models.BooleanField(_('voucher_generated'), default=False)
    created_at = models.DateTimeField(_('created date'), auto_now_add=True)

    class Meta:
        verbose_name = _('reservation')
        verbose_name_plural = _('reservations')
        ordering = ('payment_id',)

    def __str__(self):
        return self.payment_id

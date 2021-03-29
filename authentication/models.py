import base64
import datetime
import time

import pyotp
import sendgrid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from authentication.utils import list_group_uids, approve_to_group
from verifier.config import build_mail
from verifier.settings import SENDGRID_API_KEY, SECRET_KEY, SERVER_DOMAIN, MAX_VERIFY_INTERVAL_HOURS


class SteamUserManager(BaseUserManager):
    def _create_user(self, steamid, password, **extra_fields):
        """
        Creates and saves a User with the given steamid and password.
        """
        try:
            # python social auth provides an empty email param, which cannot be used here
            del extra_fields['email']
        except KeyError:
            pass
        if not steamid:
            raise ValueError('The given steamid must be set')
        user = self.model(steamid=steamid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, steamid, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(steamid, password, **extra_fields)

    def create_superuser(self, steamid, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(steamid, password, **extra_fields)


class SteamUser(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'steamid'

    steamid = models.CharField(max_length=17, unique=True)
    steamid32 = models.BigIntegerField(null=True)
    steamid64 = models.BigIntegerField(null=True)
    personaname = models.CharField(max_length=255)
    profileurl = models.CharField(max_length=300)
    avatar = models.CharField(max_length=255)
    avatarmedium = models.CharField(max_length=255)
    avatarfull = models.CharField(max_length=255)

    # Add the other fields that can be retrieved from the Web-API if required

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email = models.EmailField(_('email address'), blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    is_approved_to_group = models.BooleanField(default=False)
    last_verify_email = models.IntegerField(default=0)

    lastlogoff = models.IntegerField(null=True)
    timecreated = models.IntegerField(null=True)

    loccountrycode = models.CharField(max_length=32, null=True)
    locstatecode = models.CharField(max_length=32, null=True)

    objects = SteamUserManager()

    def get_short_name(self):
        return self.personaname

    def get_full_name(self):
        return self.personaname

    @property
    def time_created(self):
        return datetime.datetime.fromtimestamp(self.timecreated)

    @property
    def time_created_formatted(self):
        return datetime.datetime.fromtimestamp(self.timecreated).strftime("%Y-%m-%d")

    def get_totp(self):
        otp = pyotp.TOTP(
            base64.b32encode(
                (self.steamid + SECRET_KEY).encode("u8")
            ).decode("u8"), interval=300
        )
        return otp.now()

    def verify_totp(self, otp_str):
        otp = pyotp.TOTP(
            base64.b32encode(
                (self.steamid + SECRET_KEY).encode("u8")
            ).decode("u8"), interval=300
        )
        if otp.verify(otp_str, valid_window=6):
            self.is_email_verified = True
            self.save()
            return True
        return False

    def get_verify_link(self):
        return f"{SERVER_DOMAIN}/" \
               f"?action=verify" \
               f"&steamid={self.steamid}" \
               f"&verification_code={self.get_totp()}"

    @property
    def is_already_in_group(self):
        if self.is_approved_to_group:
            return True
        if self.steamid64 in list_group_uids():
            self.is_approved_to_group = True
            self.save()
            return True
        return False

    def add_to_group(self):
        if self.is_email_verified:
            if approve_to_group(self.steamid32):
                self.is_approved_to_group = self.is_already_in_group
                return True
        return False

    @property
    def can_verify_email(self):
        if self.is_already_in_group:
            return False
        if self.is_email_verified:
            return False
        return time.time() - self.last_verify_email > MAX_VERIFY_INTERVAL_HOURS * 3600

    def send_verification_mail(self):
        if self.is_already_in_group:
            return False
        if not self.can_verify_email:
            return False
        if not self.is_email_verified and self.email:
            message = build_mail(self)
            try:
                sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
                sg.send(message)
                self.last_verify_email = time.time()
                self.save()
                return True
            except Exception as e:
                print(e)
                return False

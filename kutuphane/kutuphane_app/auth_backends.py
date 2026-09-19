"""Kimlik doğrulama backend'i — kullanıcı adı büyük/küçük harf duyarsız.

Üye numarası (kullanıcı adı) farklı harf biçimlerinde girilse de (5a01 ↔ 5A01)
aynı hesaba giriş yapılabilmesi için kullanılır. Birden fazla eşleşme olursa
güvenlik gereği giriş reddedilir.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            user = UserModel.objects.get(username__iexact=username)
        except UserModel.DoesNotExist:
            # Zamanlama saldırılarını azaltmak için parola hash'i yine de çalıştırılır.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

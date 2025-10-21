from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, name=None, role = 'student', status='active', password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email = email, name = name, role = role, status = status, **extra_fields)
        user.set_unusable_password()
        user.save(using = self.db)
        return user
    
    def create_superuser(self, email, name = None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "active")
        return self.create_user(email, name, role="admin", password=password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("Student", "student"),
        ("Admin", "admin"),
    ]

    STATUS_CHOICES = [
        ("Active", "active"),
        ("Inactive", "inactive"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank = True, null = True)
    role = models.CharField(max_length=20, default = "Student")
    status = models.CharField(max_length=20, default = "Active")

    is_staff = models.BooleanField(default = False)
    is_Active = models.BooleanField(default = True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

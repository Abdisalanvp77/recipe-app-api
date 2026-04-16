"""_summary_
Django admin modifications.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core import models
from django.utils.translation import gettext_lazy as _


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""
    ordering = ['id']
    list_display = ['email', 'name']
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    fieldsets = (
        (
            None, {
                'fields': (
                    'email',
                    'password'
                )
            }
        ),
        (
            _('Personal Info'),
            {
                'fields': (
                    'name',
                )
            }
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser'
                )
            }
        ),
        (
            _('Important dates'),
            {
                'fields': (
                    'last_login',
                )
            }
        )
    )
    readonly_fields = ['last_login']  # Make last_login read-only in the admin interface.
    # The fields to be used when creating a user via the admin site.
    # These override the definitions on the base UserAdmin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'name',
                'is_active',
                'is_staff',
                'is_superuser'
            )
        }),
    )


admin.site.register(models.User, UserAdmin)  # Register the custom user model with the admin site.
admin.site.register(models.Recipe)  # Register the Recipe model with the admin site.

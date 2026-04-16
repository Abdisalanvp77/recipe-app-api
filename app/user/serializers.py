"""_summary_
Serializers for the user API View
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

# Get the user model defined in the core app,
# which is a custom user model that extends AbstractBaseUser and PermissionsMixin.
# This allows us to use the custom user model in our serializers and views
# without having to import it directly from the core app.
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for the user object."""

    class Meta:
        model = User
        fields = ('email', 'password', 'name')
        extra_kwargs = {
            'password': {
                'write_only': True,  #for security reasons, we don't want to return the password in the API response
                'min_length': 5
            }
        }

    def create(self, validated_data):
        """Create a new user."""
        return User.objects.create_user(**validated_data)

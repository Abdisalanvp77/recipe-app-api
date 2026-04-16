"""_summary_
Serializers for the user API View
"""
from django.contrib.auth import (
    get_user_model,
    authenticate
)
from rest_framework import serializers
from django.utils.translation import gettext as _

# Get the user model defined in the core app,
# which is a custom user model that extends AbstractBaseUser and PermissionsMixin.
# This allows us to use the custom user model in our serializers and views
# without having to import it directly from the core app.
# by using get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the user object."""

    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'name')
        extra_kwargs = {
            'password': {
                'write_only': True,  # for security reasons, we don't want to return the password in the API response
                'min_length': 5
            }
        }

    def create(self, validated_data):
        """Create a new user."""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update a user, setting the password correctly and return it."""
        password = validated_data.pop('password', None)  # remove the password from the validated data, if it exists, so that it is not updated as a regular field
        user = super().update(instance, validated_data)  # call the parent class's update method to update the user instance with the validated data, excluding the password

        if password:
            user.set_password(password)  # if a password was provided, set it using the set_password method, which will hash the password and save it to the database
            user.save()

        return user


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for the user authentication object."""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        """Validate and authenticate the user."""
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            msg = _('Unable to authenticate with provided credentials.')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs

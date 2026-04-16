"""_summary_
Views for the user API.
"""
from rest_framework import generics, permissions, authentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from user.serializers import (
    UserSerializer,
    AuthTokenSerializer
)


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    # we use the UserSerializer for the CreateUserView,
    # since it handles the creation of a new user correctly,
    # including hashing the password and validating the email field
    serializer_class = UserSerializer


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for the user."""
    # we use a custom serializer for the token view, since the default one does not include the email field,
    # which is required for our custom user model
    serializer_class = AuthTokenSerializer
    # we set the renderer classes to the default renderer classes, which includes the JSONRenderer,
    # so that we can get a JSON response when we create a token,
    # instead of the default browsable API response, which is not suitable for our use case
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    # we use the same serializer for creating and updating the user,
    # since it handles both cases correctly
    serializer_class = UserSerializer
    # we use token authentication for this view, since we want to authenticate the user using a token,
    # and we want to ensure that only authenticated users can access this view
    authentication_classes = [authentication.TokenAuthentication]
    # we set the permission classes to IsAuthenticated,
    # since we want to ensure that only authenticated users can access this view
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrieve and return the authenticated user."""
        return self.request.user

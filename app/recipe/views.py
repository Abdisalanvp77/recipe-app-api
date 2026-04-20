"""
Views for the recipe APIs
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Q
from django.http import Http404
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes
)
from rest_framework import (
    viewsets,
    mixins,
    permissions
)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from core.models import (
    Recipe,
    Rating,
    Tag,
    Ingredient,
    DietaryRestriction,
    GlobalTag,
    GlobalIngredient,
    RecipeCollection,
    CollectionRecipe,
)
from recipe import serializers


class IsRecipeOwnerOrReadOnly(permissions.BasePermission):
    """Allow safe recipe access, respecting privacy settings. Edit only by owner or admin."""

    def has_object_permission(self, request, view, obj):
        # Safe methods require respecting privacy
        if request.method in permissions.SAFE_METHODS:
            # if the recipe is draft, only the owner or admin can view it
            if obj.status == 'draft':
                return obj.user == request.user or request.user.is_superuser
            # If the recipe is private, only the owner or admin can view it
            if obj.status == 'private':
                return obj.user == request.user or request.user.is_superuser
            return obj.status in ['published']  # Published visible to all auth users

        # Only owner or admin can edit/delete
        return obj.user == request.user or request.user.is_superuser


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'tags',
                OpenApiTypes.STR,
                description='Comma separated list of tag IDs to filter',
                required=False
            ),
            OpenApiParameter(
                'ingredients',
                OpenApiTypes.STR,
                description='Comma separated list of ingredient IDs to filter',
                required=False
            ),
            OpenApiParameter(
                'rating',
                OpenApiTypes.NUMBER,
                description='Filter recipes with average rating greater than or equal to this value',
                required=False
            )
        ]
    )
)
class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIs
    """
    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsRecipeOwnerOrReadOnly]

    def _params_to_ints(self, qs):
        """Convert a list of string IDs to a list of integers."""
        return [int(str_id) for str_id in qs.split(',')]

    def get_queryset(self):
        """Return objects for all authenticated users with optional filtering."""
        tags = self.request.query_params.get('tags')
        ingredients = self.request.query_params.get('ingredients')
        rating = self.request.query_params.get('rating')
        cuisine = self.request.query_params.get('cuisine')
        difficulty = self.request.query_params.get('difficulty')
        is_vegetarian = self.request.query_params.get('is_vegetarian')
        is_vegan = self.request.query_params.get('is_vegan')

        queryset = self.queryset.annotate(avg_rating=Avg('ratings__rating'))

        # Filter by privacy settings: show published/draft to all, private only to owner
        queryset = queryset.filter(
            Q(status__in=['published', 'draft']) | Q(user=self.request.user)
        )

        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)

        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        if rating is not None:
            try:
                rating_threshold = Decimal(rating)
                queryset = queryset.filter(avg_rating__gte=rating_threshold)
            except InvalidOperation:
                queryset = queryset.none()

        if cuisine:
            queryset = queryset.filter(cuisine__icontains=cuisine)

        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if is_vegetarian:
            queryset = queryset.filter(is_vegetarian=is_vegetarian.lower() == 'true')

        if is_vegan:
            queryset = queryset.filter(is_vegan=is_vegan.lower() == 'true')

        return queryset.order_by('-id').distinct()

    def perform_create(self, serializer):
        """Create a new recipe"""
        # Set the user to the current authenticated user when creating a new recipe
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return serializers.RecipeSerializer
        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer
        return self.serializer_class

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to a recipe."""
        recipe = self.get_object()
        serializer = self.get_serializer(
            recipe,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IsRatingOwnerOrReadOnly(permissions.BasePermission):
    """Allow owners to edit/delete their rating, others read-only."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_superuser


class RatingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recipe ratings."""
    serializer_class = serializers.RecipeRatingSerializer
    queryset = Rating.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsRatingOwnerOrReadOnly]

    def get_queryset(self):
        queryset = self.queryset.order_by('-id')
        recipe_id = self.kwargs.get('recipe_id')
        if recipe_id:
            queryset = queryset.filter(recipe__id=recipe_id)
        return queryset

    def get_object(self):
        """Get the rating object for the specified recipe and current or target user."""
        recipe_id = self.kwargs.get('recipe_id')
        target_user_id = self.request.query_params.get('user')

        if self.request.user.is_superuser and target_user_id:
            try:
                return Rating.objects.get(user__id=target_user_id, recipe__id=recipe_id)
            except Rating.DoesNotExist:
                raise Http404("Rating not found for the specified user and recipe.")

        try:
            return Rating.objects.get(user=self.request.user, recipe__id=recipe_id)
        except Rating.DoesNotExist:
            raise Http404("You haven't rated this recipe yet.")

    def list(self, request, recipe_id=None):
        """List all ratings for a specific recipe."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, recipe_id=None):
        """Create or update a rating for a specific recipe."""
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"error": "Recipe not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating_value = serializer.validated_data['rating']

        rating_obj, created = Rating.objects.update_or_create(
            user=request.user,
            recipe=recipe,
            defaults={'rating': rating_value}
        )
        output_serializer = self.get_serializer(rating_obj)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(output_serializer.data, status=status_code)

    def partial_update(self, request, recipe_id=None):
        """Update the user's rating for a specific recipe."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, recipe_id=None):
        """Delete the user's rating for a specific recipe."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT,
                enum=[0, 1],
                description='Filter by items assigned to recipes.'
            )
        ]
    )
)
class BaseRecipeAttrViewSet(
                mixins.DestroyModelMixin,
                mixins.CreateModelMixin,
                mixins.UpdateModelMixin,
                mixins.ListModelMixin,
                viewsets.GenericViewSet):
    """Base viewset for user owned recipe attributes"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return objects for the current authenticated user only"""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
            )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.filter(user=self.request.user).order_by('-name').distinct()

    def perform_create(self, serializer):
        """Create a new ingredient"""
        # Set the user to the current authenticated user when creating a new ingredient
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        return self.serializer_class


# The TagViewSet is a viewset that provides list and
# create actions for the Tag model.
# It uses the TagSerializer to serialize the data and
# requires token authentication and that the user is authenticated.
# The get_queryset method filters the tags to return only those that belong
# to the current authenticated user, and the perform_create method sets the
# user to the current authenticated user when creating a new tag.
class TagViewSet(BaseRecipeAttrViewSet):
    """View for manage tag APIs
    """
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeAttrViewSet):
    """View for manage ingredient APIs
    """
    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()


class DietaryRestrictionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for dietary restrictions (read-only)."""
    serializer_class = serializers.DietaryRestrictionSerializer
    queryset = DietaryRestriction.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class GlobalTagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for global tags (read-only)."""
    serializer_class = serializers.GlobalTagSerializer
    queryset = GlobalTag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class GlobalIngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for global ingredients (read-only)."""
    serializer_class = serializers.GlobalIngredientSerializer
    queryset = GlobalIngredient.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class IsCollectionOwnerOrReadOnly(permissions.BasePermission):
    """Allow reading public collections, but editing only by owner or admin."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user == request.user or request.user.is_superuser
        return obj.user == request.user or request.user.is_superuser


class RecipeCollectionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recipe collections."""
    serializer_class = serializers.RecipeCollectionSerializer
    queryset = RecipeCollection.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsCollectionOwnerOrReadOnly]

    def get_queryset(self):
        """Return collections for current user and public collections."""
        return RecipeCollection.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        """Create a collection for the current user."""
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, serializer_class=serializers.CollectionRecipeActionSerializer)
    def add_recipe(self, request, pk=None):
        """Add a recipe to a collection."""
        collection = self.get_object()
        recipe_id = request.data.get('recipe_id')
        notes = request.data.get('notes', '')

        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Recipe not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if recipe is already in collection
        if collection.recipes.filter(id=recipe_id).exists():
            return Response(
                {'detail': 'Recipe is already in this collection.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        CollectionRecipe.objects.create(
            collection=collection,
            recipe=recipe,
            notes=notes
        )

        return Response(
            {'detail': 'Recipe added to collection.'},
            status=status.HTTP_201_CREATED
        )

    def remove_recipe(self, request, pk=None, recipe_id=None):
        """Remove a recipe from a collection."""
        collection = self.get_object()

        if recipe_id is None:
            return Response(
                {'detail': 'Recipe ID is required in the URL path.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Recipe not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            CollectionRecipe.objects.get(
                collection=collection,
                recipe=recipe
            ).delete()
        except CollectionRecipe.DoesNotExist:
            return Response(
                {'detail': 'Recipe not found in this collection.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

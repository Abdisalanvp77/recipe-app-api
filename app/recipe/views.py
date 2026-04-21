"""
Views for the recipe APIs
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
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
        description="List and search recipes with advanced filtering options.",
        parameters=[
            OpenApiParameter(
                'search',
                OpenApiTypes.STR,
                description='Full-text search across recipe titles, descriptions, ingredients, and tags',
                required=False
            ),
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
                'global_tags',
                OpenApiTypes.STR,
                description='Comma separated list of global tag IDs to filter',
                required=False
            ),
            OpenApiParameter(
                'global_ingredients',
                OpenApiTypes.STR,
                description='Comma separated list of global ingredient IDs to filter',
                required=False
            ),
            OpenApiParameter(
                'dietary_restrictions',
                OpenApiTypes.STR,
                description='Comma separated list of dietary restriction IDs to filter',
                required=False
            ),
            OpenApiParameter(
                'cuisine',
                OpenApiTypes.STR,
                description='Filter by cuisine type',
                required=False
            ),
            OpenApiParameter(
                'difficulty',
                OpenApiTypes.STR,
                description='Filter by difficulty (easy, medium, hard)',
                required=False
            ),
            OpenApiParameter(
                'min_rating',
                OpenApiTypes.NUMBER,
                description='Filter recipes with average rating greater than or equal to this value',
                required=False
            ),
            OpenApiParameter(
                'max_rating',
                OpenApiTypes.NUMBER,
                description='Filter recipes with average rating less than or equal to this value',
                required=False
            ),
            OpenApiParameter(
                'min_price',
                OpenApiTypes.NUMBER,
                description='Filter recipes with price greater than or equal to this value',
                required=False
            ),
            OpenApiParameter(
                'max_price',
                OpenApiTypes.NUMBER,
                description='Filter recipes with price less than or equal to this value',
                required=False
            ),
            OpenApiParameter(
                'max_prep_time',
                OpenApiTypes.INT,
                description='Filter recipes with prep time less than or equal to this value (minutes)',
                required=False
            ),
            OpenApiParameter(
                'max_cook_time',
                OpenApiTypes.INT,
                description='Filter recipes with cook time less than or equal to this value (minutes)',
                required=False
            ),
            OpenApiParameter(
                'max_total_time',
                OpenApiTypes.INT,
                description='Filter recipes with total time less than or equal to this value (minutes)',
                required=False
            ),
            OpenApiParameter(
                'is_vegetarian',
                OpenApiTypes.BOOL,
                description='Filter vegetarian recipes only',
                required=False
            ),
            OpenApiParameter(
                'is_vegan',
                OpenApiTypes.BOOL,
                description='Filter vegan recipes only',
                required=False
            ),
            OpenApiParameter(
                'is_gluten_free',
                OpenApiTypes.BOOL,
                description='Filter gluten-free recipes only',
                required=False
            ),
            OpenApiParameter(
                'sort_by',
                OpenApiTypes.STR,
                description='Sort results by: created_at, updated_at, rating, price, time_minutes, prep_time_minutes, cook_time_minutes, title',
                required=False
            ),
            OpenApiParameter(
                'sort_order',
                OpenApiTypes.STR,
                description='Sort order: asc or desc (default: desc)',
                required=False
            ),
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
        """Return objects for all authenticated users with advanced filtering and search."""
        queryset = self.queryset.annotate(avg_rating=Avg('ratings__rating'))

        # Filter by privacy settings: show published/draft to all, private only to owner
        queryset = queryset.filter(
            Q(status__in=['published', 'draft']) | Q(user=self.request.user)
        )

        # Full-text search
        search_query = self.request.query_params.get('search')
        if search_query:
            search_vector = SearchVector('title', weight='A') + \
                           SearchVector('description', weight='B') + \
                           SearchVector('cuisine', weight='C')
            search_q = SearchQuery(search_query)
            queryset = queryset.annotate(
                search_rank=SearchRank(search_vector, search_q)
            ).filter(search_vector=search_q).order_by('-search_rank')

        # Tag filters
        tags = self.request.query_params.get('tags')
        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)

        global_tags = self.request.query_params.get('global_tags')
        if global_tags:
            global_tag_ids = self._params_to_ints(global_tags)
            queryset = queryset.filter(tags__name__in=[
                GlobalTag.objects.get(id=gt_id).name for gt_id in global_tag_ids
            ])

        # Ingredient filters
        ingredients = self.request.query_params.get('ingredients')
        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        global_ingredients = self.request.query_params.get('global_ingredients')
        if global_ingredients:
            global_ingredient_ids = self._params_to_ints(global_ingredients)
            queryset = queryset.filter(ingredients__name__in=[
                GlobalIngredient.objects.get(id=gi_id).name for gi_id in global_ingredient_ids
            ])

        # Dietary restrictions
        dietary_restrictions = self.request.query_params.get('dietary_restrictions')
        if dietary_restrictions:
            restriction_ids = self._params_to_ints(dietary_restrictions)
            queryset = queryset.filter(dietary_restrictions__id__in=restriction_ids)

        # Basic filters
        cuisine = self.request.query_params.get('cuisine')
        if cuisine:
            queryset = queryset.filter(cuisine__icontains=cuisine)

        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        # Rating filters (support both old 'rating' param and new min_rating for backward compatibility)
        min_rating = self.request.query_params.get('min_rating') or self.request.query_params.get('rating')
        if min_rating:
            try:
                min_rating_val = Decimal(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating_val)
            except InvalidOperation:
                pass

        max_rating = self.request.query_params.get('max_rating')
        if max_rating:
            try:
                max_rating_val = Decimal(max_rating)
                queryset = queryset.filter(avg_rating__lte=max_rating_val)
            except InvalidOperation:
                pass

        # Price filters
        min_price = self.request.query_params.get('min_price')
        if min_price:
            try:
                min_price_val = Decimal(min_price)
                queryset = queryset.filter(price__gte=min_price_val)
            except InvalidOperation:
                pass

        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                max_price_val = Decimal(max_price)
                queryset = queryset.filter(price__lte=max_price_val)
            except InvalidOperation:
                pass

        # Time filters
        max_prep_time = self.request.query_params.get('max_prep_time')
        if max_prep_time:
            try:
                max_prep_val = int(max_prep_time)
                queryset = queryset.filter(prep_time_minutes__lte=max_prep_val)
            except ValueError:
                pass

        max_cook_time = self.request.query_params.get('max_cook_time')
        if max_cook_time:
            try:
                max_cook_val = int(max_cook_time)
                queryset = queryset.filter(cook_time_minutes__lte=max_cook_val)
            except ValueError:
                pass

        max_total_time = self.request.query_params.get('max_total_time')
        if max_total_time:
            try:
                max_total_val = int(max_total_time)
                queryset = queryset.filter(
                    prep_time_minutes__lte=max_total_val,
                    cook_time_minutes__lte=max_total_val
                ).filter(
                    F('prep_time_minutes') + F('cook_time_minutes') <= max_total_val
                )
            except ValueError:
                pass

        # Boolean filters
        is_vegetarian = self.request.query_params.get('is_vegetarian')
        if is_vegetarian:
            queryset = queryset.filter(is_vegetarian=is_vegetarian.lower() == 'true')

        is_vegan = self.request.query_params.get('is_vegan')
        if is_vegan:
            queryset = queryset.filter(is_vegan=is_vegan.lower() == 'true')

        is_gluten_free = self.request.query_params.get('is_gluten_free')
        if is_gluten_free:
            queryset = queryset.filter(is_gluten_free=is_gluten_free.lower() == 'true')

        # Sorting
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        sort_order = self.request.query_params.get('sort_order', 'desc')

        valid_sort_fields = {
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'rating': 'avg_rating',
            'price': 'price',
            'time_minutes': 'time_minutes',
            'prep_time_minutes': 'prep_time_minutes',
            'cook_time_minutes': 'cook_time_minutes',
            'title': 'title',
        }

        if sort_by in valid_sort_fields:
            sort_field = valid_sort_fields[sort_by]
            if sort_order.lower() == 'asc':
                queryset = queryset.order_by(sort_field)
            else:
                queryset = queryset.order_by(f'-{sort_field}')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset.distinct()

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
    """ViewSet for managing recipe ratings and reviews."""
    serializer_class = serializers.RecipeRatingSerializer
    queryset = Rating.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsRatingOwnerOrReadOnly]

    def get_queryset(self):
        queryset = self.queryset.select_related('user', 'recipe').order_by('-created_at')
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
        """Create or update a rating/review for a specific recipe."""
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"error": "Recipe not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if user already has a rating for this recipe
        existing_rating = Rating.objects.filter(user=request.user, recipe=recipe).first()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating_data = {
            'rating': serializer.validated_data['rating'],
            'review_text': serializer.validated_data.get('review_text', ''),
        }

        rating_obj, created = Rating.objects.update_or_create(
            user=request.user,
            recipe=recipe,
            defaults=rating_data
        )

        output_serializer = self.get_serializer(rating_obj)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(output_serializer.data, status=status_code)

    def partial_update(self, request, recipe_id=None):
        """Update the user's rating/review for a specific recipe."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, recipe_id=None):
        """Delete the user's rating/review for a specific recipe."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=True, url_path='vote')
    def vote_helpful(self, request, pk=None, recipe_id=None):
        """Vote on whether a review is helpful."""
        rating = self.get_object()
        is_helpful = request.data.get('is_helpful', True)

        vote, created = ReviewVote.objects.update_or_create(
            user=request.user,
            rating=rating,
            defaults={'is_helpful': is_helpful}
        )

        # Update vote counts on the rating
        rating.total_votes = rating.votes.count()
        rating.helpful_votes = rating.votes.filter(is_helpful=True).count()
        rating.save()

        return Response({
            'message': 'Vote recorded successfully',
            'helpful_votes': rating.helpful_votes,
            'total_votes': rating.total_votes,
            'helpful_percentage': rating.helpful_percentage
        })


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


class DietaryRestrictionViewSet(viewsets.ModelViewSet):
    """ViewSet for dietary restrictions."""
    serializer_class = serializers.DietaryRestrictionSerializer
    queryset = DietaryRestriction.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow read access to all authenticated users, write access to admins."""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


@extend_schema_view(
    list=extend_schema(
        description="List all global tags available for recipe categorization."
    ),
    create=extend_schema(
        description="Create a new global tag (admin only)."
    ),
    retrieve=extend_schema(
        description="Retrieve a specific global tag."
    ),
    update=extend_schema(
        description="Update a global tag (admin only)."
    ),
    partial_update=extend_schema(
        description="Partially update a global tag (admin only)."
    ),
    destroy=extend_schema(
        description="Delete a global tag (admin only)."
    )
)
class GlobalTagViewSet(viewsets.ModelViewSet):
    """ViewSet for global tags."""
    serializer_class = serializers.GlobalTagSerializer
    queryset = GlobalTag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow read access to all authenticated users, write access to admins."""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


@extend_schema_view(
    list=extend_schema(
        description="List all global ingredients available for recipe categorization."
    ),
    create=extend_schema(
        description="Create a new global ingredient (admin only)."
    ),
    retrieve=extend_schema(
        description="Retrieve a specific global ingredient."
    ),
    update=extend_schema(
        description="Update a global ingredient (admin only)."
    ),
    partial_update=extend_schema(
        description="Partially update a global ingredient (admin only)."
    ),
    destroy=extend_schema(
        description="Delete a global ingredient (admin only)."
    )
)
class GlobalIngredientViewSet(viewsets.ModelViewSet):
    """ViewSet for global ingredients."""
    serializer_class = serializers.GlobalIngredientSerializer
    queryset = GlobalIngredient.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow read access to all authenticated users, write access to admins."""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


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

"""Serializers for the recipe API."""
from rest_framework import serializers
from core.models import (
    Ingredient,
    Recipe,
    Rating,
    ReviewVote,
    Tag,
    RecipeStep,
    DietaryRestriction,
    GlobalTag,
    GlobalIngredient,
    RecipeCollection,
    CollectionRecipe,
)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag objects."""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredient objects."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']


class DietaryRestrictionSerializer(serializers.ModelSerializer):
    """Serializer for dietary restriction objects."""

    class Meta:
        model = DietaryRestriction
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']


class GlobalTagSerializer(serializers.ModelSerializer):
    """Serializer for global tag objects."""

    class Meta:
        model = GlobalTag
        fields = ['id', 'name', 'slug', 'usage_count', 'created_at']
        read_only_fields = ['id', 'slug', 'usage_count', 'created_at']


class GlobalIngredientSerializer(serializers.ModelSerializer):
    """Serializer for global ingredient objects."""

    class Meta:
        model = GlobalIngredient
        fields = ['id', 'name', 'slug', 'usage_count', 'created_at']
        read_only_fields = ['id', 'slug', 'usage_count', 'created_at']


class RecipeStepSerializer(serializers.ModelSerializer):
    """Serializer for recipe steps."""

    class Meta:
        model = RecipeStep
        fields = ['id', 'step_number', 'instruction', 'optional_timer_minutes', 'notes']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe objects."""
    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)
    steps = RecipeStepSerializer(many=True, required=False, read_only=True)
    dietary_restrictions = DietaryRestrictionSerializer(many=True, required=False)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id',
            'title',
            'status',
            'time_minutes',
            'prep_time_minutes',
            'cook_time_minutes',
            'servings',
            'price',
            'link',
            'description',
            'difficulty',
            'cuisine',
            'is_vegetarian',
            'is_vegan',
            'is_gluten_free',
            'tags',
            'ingredients',
            'dietary_restrictions',
            'steps',
            'average_rating',
            'rating_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'steps', 'created_at', 'updated_at']

    def get_average_rating(self, obj):
        return obj.average_rating

    def get_rating_count(self, obj):
        return obj.rating_count

    def _get_or_create_ingredients(self, ingredients_data, recipe):
        """Handle getting or creating ingredients as needed."""
        authenticated_user = self.context['request'].user
        for ingredient_data in ingredients_data:
            ingredient, created = Ingredient.objects.get_or_create(
                user=authenticated_user,
                **ingredient_data
            )
            recipe.ingredients.add(ingredient)

    def _get_or_create_tags(self, tags_data, recipe):
        """Handle getting or creating tags as needed."""
        authenticated_user = self.context['request'].user
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                user=authenticated_user,
                **tag_data
            )
            recipe.tags.add(tag)

    def create(self, validated_data):
        """Create a recipe."""
        tags_data = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        dietary_restrictions_data = validated_data.pop('dietary_restrictions', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags_data, recipe)
        self._get_or_create_ingredients(ingredients_data, recipe)
        for restriction in dietary_restrictions_data:
            recipe.dietary_restrictions.add(restriction)

        return recipe

    def update(self, instance, validated_data):
        """Update a recipe."""
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        dietary_restrictions_data = validated_data.pop('dietary_restrictions', None)

        if tags_data is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags_data, instance)

        if ingredients_data is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients_data, instance)

        if dietary_restrictions_data is not None:
            instance.dietary_restrictions.clear()
            for restriction in dietary_restrictions_data:
                instance.dietary_restrictions.add(restriction)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeRatingSerializer(serializers.ModelSerializer):
    """Serializer for recipe rating objects."""
    user = serializers.StringRelatedField(read_only=True)
    recipe = serializers.PrimaryKeyRelatedField(read_only=True)
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, min_value=1, max_value=5)
    helpful_percentage = serializers.SerializerMethodField()
    user_has_voted = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = [
            'id', 'user', 'recipe', 'rating', 'review_text',
            'created_at', 'updated_at', 'is_verified',
            'helpful_votes', 'total_votes', 'helpful_percentage', 'user_has_voted'
        ]
        read_only_fields = [
            'id', 'user', 'recipe', 'created_at', 'updated_at',
            'helpful_votes', 'total_votes', 'helpful_percentage', 'user_has_voted'
        ]

    def get_helpful_percentage(self, obj):
        return obj.helpful_percentage

    def get_user_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.votes.filter(user=request.user).exists()
        return False


class ReviewVoteSerializer(serializers.ModelSerializer):
    """Serializer for review vote objects."""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    rating = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ReviewVote
        fields = ['id', 'user', 'rating', 'is_helpful', 'created_at']
        read_only_fields = ['id', 'user', 'rating', 'created_at']


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail view."""

    ratings = RecipeRatingSerializer(many=True, read_only=True)

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['ratings']


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipes."""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}


class CollectionRecipeSerializer(serializers.ModelSerializer):
    """Serializer for collection recipes."""
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = CollectionRecipe
        fields = ['id', 'recipe', 'added_at', 'notes']
        read_only_fields = ['id', 'recipe', 'added_at']


class RecipeCollectionSerializer(serializers.ModelSerializer):
    """Serializer for recipe collections."""
    collection_recipes = serializers.SerializerMethodField()
    recipe_count = serializers.SerializerMethodField()

    class Meta:
        model = RecipeCollection
        fields = ['id', 'name', 'description', 'is_public', 'created_at', 'updated_at', 'recipe_count', 'collection_recipes']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_collection_recipes(self, obj):
        """Return collection recipes with metadata."""
        collection_recipes = CollectionRecipe.objects.filter(collection=obj)
        return CollectionRecipeSerializer(collection_recipes, many=True).data

    def get_recipe_count(self, obj):
        """Return the number of recipes in the collection."""
        return obj.recipes.count()


class CollectionRecipeActionSerializer(serializers.Serializer):
    """Serializer for add/remove recipe actions on collections."""
    recipe_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)

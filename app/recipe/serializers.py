"""Serializers for the recipe API."""
from rest_framework import serializers
from core.models import Ingredient, Recipe, Rating, Tag


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


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe objects."""
    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id',
            'title',
            'time_minutes',
            'price',
            'link',
            'tags',
            'ingredients',
            'average_rating',
            'rating_count'
        ]
        read_only_fields = ['id']

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
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags_data, recipe)
        self._get_or_create_ingredients(ingredients_data, recipe)

        return recipe

    def update(self, instance, validated_data):
        """Update a recipe."""
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        if tags_data is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags_data, instance)

        if ingredients_data is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients_data, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeRatingSerializer(serializers.ModelSerializer):
    """Serializer for recipe rating objects."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    recipe = serializers.PrimaryKeyRelatedField(read_only=True)
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, min_value=1, max_value=5)

    class Meta:
        model = Rating
        fields = ['id', 'user', 'recipe', 'rating']
        read_only_fields = ['id', 'user', 'recipe']


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail view."""

    ratings = RecipeRatingSerializer(many=True, read_only=True)

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description', 'image', 'ratings']


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipes."""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}

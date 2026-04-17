"""Serializers for the recipe API."""
from rest_framework import serializers
from core.models import Recipe, Tag


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag objects."""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe objects."""
    tags = TagSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

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
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags_data, recipe)

        return recipe

    def update(self, instance, validated_data):
        """Update a recipe."""
        tags_data = validated_data.pop('tags', None)
        if tags_data is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags_data, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail view."""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']

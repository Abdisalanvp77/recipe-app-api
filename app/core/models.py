"""
Model definitions for the core app.
"""


import uuid
import os
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.contrib.postgres.search import SearchVectorField, SearchVector


def recipe_image_file_path(instance, filename):
    """Generate file path for new recipe image."""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'

    return os.path.join('uploads', 'recipe', filename)


class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a new user."""
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create and save a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system model."""
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = 'email'


class Recipe(models.Model):
    """Recipe object."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('private', 'Private'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    time_minutes = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    tags = models.ManyToManyField('Tag')
    ingredients = models.ManyToManyField('Ingredient')
    image = models.ImageField(null=True, upload_to=recipe_image_file_path)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )
    servings = models.PositiveIntegerField(default=4)
    prep_time_minutes = models.PositiveIntegerField(default=0)
    cook_time_minutes = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium'
    )
    cuisine = models.CharField(max_length=100, blank=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    dietary_restrictions = models.ManyToManyField('DietaryRestriction', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['cuisine']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['is_vegetarian', 'is_vegan', 'is_gluten_free']),
            models.Index(fields=['search_vector']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update search vector
        self.search_vector = (
            SearchVector('title', weight='A') +
            SearchVector('description', weight='B') +
            SearchVector('cuisine', weight='C')
        )
        # Add ingredient and tag names to search
        ingredient_names = ' '.join([ing.name for ing in self.ingredients.all()])
        tag_names = ' '.join([tag.name for tag in self.tags.all()])
        if ingredient_names:
            self.search_vector += SearchVector(models.Value(ingredient_names), weight='D')
        if tag_names:
            self.search_vector += SearchVector(models.Value(tag_names), weight='D')
        super().save(update_fields=['search_vector'])

    @property
    def average_rating(self):
        """Return the average rating for the recipe."""
        aggregate = self.ratings.aggregate(models.Avg('rating'))['rating__avg']
        return round(aggregate, 2) if aggregate is not None else None

    @property
    def rating_count(self):
        """Return the total number of ratings for the recipe."""
        return self.ratings.count()

    @property
    def total_time_minutes(self):
        """Return total time (prep + cook)."""
        return self.prep_time_minutes + self.cook_time_minutes

    def __str__(self):
        return self.title


class Rating(models.Model):
    """Rating given by a user to a recipe."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='ratings',
        on_delete=models.CASCADE
    )
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_verified = models.BooleanField(default=False)  # Verified purchase/review
    helpful_votes = models.PositiveIntegerField(default=0)
    total_votes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'recipe')
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='rating_range_1_5'
            )
        ]

    @property
    def helpful_percentage(self):
        """Return the percentage of helpful votes."""
        if self.total_votes == 0:
            return 0
        return round((self.helpful_votes / self.total_votes) * 100, 1)

    def __str__(self):
        return f'{self.rating} rating for {self.recipe.title}'


class ReviewVote(models.Model):
    """Helpful/not helpful votes on reviews."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    rating = models.ForeignKey(
        Rating,
        related_name='votes',
        on_delete=models.CASCADE
    )
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'rating')

    def __str__(self):
        return f'{"Helpful" if self.is_helpful else "Not helpful"} vote by {self.user.email}'


class Tag(models.Model):
    """Tag for filtering recipes."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Ingredient for filtering recipes."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class RecipeStep(models.Model):
    """Recipe step/instruction."""
    recipe = models.ForeignKey(Recipe, related_name='steps', on_delete=models.CASCADE)
    step_number = models.PositiveIntegerField()
    instruction = models.TextField()
    optional_timer_minutes = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['step_number']
        unique_together = ['recipe', 'step_number']

    def __str__(self):
        return f'Step {self.step_number} of {self.recipe.title}'


class DietaryRestriction(models.Model):
    """Dietary restriction/preference."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while DietaryRestriction.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GlobalTag(models.Model):
    """Global tag for taxonomy and discoverability."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-usage_count', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while GlobalTag.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GlobalIngredient(models.Model):
    """Global ingredient for taxonomy and discoverability."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-usage_count', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while GlobalIngredient.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class RecipeCollection(models.Model):
    """User-created collection of recipes for bookmarking and organization."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipe_collections'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    recipes = models.ManyToManyField(Recipe, through='CollectionRecipe', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return f'{self.user.email} - {self.name}'


class CollectionRecipe(models.Model):
    """Intermediate model for RecipeCollection with additional metadata."""
    collection = models.ForeignKey(RecipeCollection, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    added_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ['collection', 'recipe']

    def __str__(self):
        return f'{self.collection.name} - {self.recipe.title}'

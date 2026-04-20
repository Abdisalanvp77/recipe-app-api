"""_summary_
Tests for the recipe API.
"""
from decimal import Decimal
import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient, Recipe, Rating, Tag
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')


# Helper function to create a recipe detail URL
def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Return URL for recipe image upload."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


# Helper functions to create sample data for testing
# These functions are used to create sample recipes, tags, and ingredients for testing purposes.
def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    # Update the defaults with any parameters passed in,
    # allowing us to create recipes with different attributes for testing.
    defaults.update(params)
    # Create and return a recipe instance using the provided user
    # and the updated defaults.
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_rate_recipe(self):
        """Test rating a recipe."""
        recipe = create_recipe(user=self.user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id])
        payload = {'rating': Decimal('4.5')}

        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipe.ratings.get(user=self.user).rating, Decimal('4.5'))

    def test_update_recipe_rating(self):
        """Test updating a recipe rating."""
        recipe = create_recipe(user=self.user)
        recipe.ratings.create(user=self.user, rating=Decimal('2.0'))
        url = reverse('recipe:recipe-ratings', args=[recipe.id])
        payload = {'rating': Decimal('4.5')}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ratings.get(user=self.user).rating, Decimal('4.5'))

    def test_delete_own_rating(self):
        """Test deleting your own rating."""
        recipe = create_recipe(user=self.user)
        Rating.objects.create(user=self.user, recipe=recipe, rating=Decimal('4.0'))
        url = reverse('recipe:recipe-ratings', args=[recipe.id])

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Rating.objects.filter(user=self.user, recipe=recipe).exists())

    def test_cannot_delete_other_users_rating(self):
        """Test that a user cannot delete another user's rating."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe = create_recipe(user=self.user)
        Rating.objects.create(user=other_user, recipe=recipe, rating=Decimal('3.0'))
        url = reverse('recipe:recipe-ratings', args=[recipe.id])

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Rating.objects.filter(user=other_user, recipe=recipe).exists())

    def test_admin_can_update_other_users_rating(self):
        """Test that an admin can update another user's rating."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        recipe = create_recipe(user=self.user)
        Rating.objects.create(user=other_user, recipe=recipe, rating=Decimal('3.0'))
        self.client.force_authenticate(user=admin_user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id]) + f'?user={other_user.id}'
        payload = {'rating': Decimal('4.0')}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Rating.objects.get(user=other_user, recipe=recipe).rating, Decimal('4.0'))

    def test_admin_can_delete_other_users_rating(self):
        """Test that an admin can delete another user's rating."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        recipe = create_recipe(user=self.user)
        Rating.objects.create(user=other_user, recipe=recipe, rating=Decimal('3.0'))
        self.client.force_authenticate(user=admin_user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id]) + f'?user={other_user.id}'

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Rating.objects.filter(user=other_user, recipe=recipe).exists())

    def test_update_rating_when_none_exists(self):
        """Test updating a rating when user hasn't rated the recipe yet."""
        recipe = create_recipe(user=self.user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id])
        payload = {'rating': Decimal('4.0')}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_rating_when_none_exists(self):
        """Test deleting a rating when user hasn't rated the recipe yet."""
        recipe = create_recipe(user=self.user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id])

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_rate_nonexistent_recipe(self):
        """Test rating a recipe that doesn't exist."""
        url = reverse('recipe:recipe-ratings', args=[999])
        payload = {'rating': Decimal('4.0')}

        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_rating_invalid_value(self):
        """Test rating a recipe with an invalid value."""
        recipe = create_recipe(user=self.user)
        url = reverse('recipe:recipe-ratings', args=[recipe.id])
        payload = {'rating': Decimal('6.0')}

        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recipe_detail_includes_ratings(self):
        """Test recipe detail includes ratings from all users."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe = create_recipe(user=self.user)
        Rating.objects.create(user=self.user, recipe=recipe, rating=Decimal('4.0'))
        Rating.objects.create(user=other_user, recipe=recipe, rating=Decimal('5.0'))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['average_rating'], Decimal('4.5'))
        self.assertEqual(res.data['rating_count'], 2)
        self.assertEqual(len(res.data['ratings']), 2)

    def test_list_ratings_for_recipe(self):
        """Test listing ratings for a specific recipe."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe = create_recipe(user=self.user)
        other_recipe = create_recipe(user=self.user)
        rating1 = Rating.objects.create(user=self.user, recipe=recipe, rating=Decimal('4.0'))
        rating2 = Rating.objects.create(user=other_user, recipe=recipe, rating=Decimal('5.0'))
        Rating.objects.create(user=self.user, recipe=other_recipe, rating=Decimal('3.0'))

        url = reverse('recipe:recipe-ratings', args=[recipe.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        rating_ids = [rating['id'] for rating in res.data]
        self.assertIn(rating1.id, rating_ids)
        self.assertIn(rating2.id, rating_ids)

    def test_recipe_list_includes_average_rating(self):
        """Test average rating is included in recipe responses."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe = create_recipe(user=self.user)
        recipe.ratings.create(user=self.user, rating=Decimal('4.0'))
        recipe.ratings.create(user=other_user, rating=Decimal('5.0'))

        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['average_rating'], Decimal('4.5'))
        self.assertEqual(res.data[0]['rating_count'], 2)

    def test_filter_recipes_by_rating(self):
        """Test filtering recipes by average rating."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe1 = create_recipe(user=self.user)
        recipe2 = create_recipe(user=self.user)
        recipe1.ratings.create(user=self.user, rating=Decimal('3.0'))
        recipe1.ratings.create(user=other_user, recipe=recipe1, rating=Decimal('4.0'))
        recipe2.ratings.create(user=self.user, rating=Decimal('2.0'))

        res = self.client.get(RECIPES_URL, {'rating': '3.5'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe1.id)

    def test_retrieve_all_recipes(self):
        """Test retrieving recipes from all authenticated users."""

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe."""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.00'),
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_recipe_detail(self):
        """Test viewing a recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_partial_update(self):
        """Test updating a recipe with patch."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link=original_link
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test updating a recipe with put."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link='https://example.com/recipe.pdf'
        )

        payload = {
            'title': 'New recipe title',
            'time_minutes': 25,
            'price': Decimal('4.00'),
            'description': 'New description',
            'link': 'https://example.com/new-recipe.pdf'
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(
            email='newuser@example.com',
            password='newpass123'
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """Test trying to delete another user's recipe gives error."""
        new_user = create_user(
            email='newuser@example.com',
            password='newpass123'
        )
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_admin_can_update_other_users_recipe(self):
        """Test that an admin can update another user's recipe."""
        other_user = create_user(
            email='otheruser@example.com',
            password='otherpass123'
        )
        admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        recipe = create_recipe(user=other_user)
        self.client.force_authenticate(user=admin_user)

        payload = {'title': 'Updated Title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, 'Updated Title')

    def test_admin_can_delete_other_users_recipe(self):
        """Test that an admin can delete another user's recipe."""
        other_user = create_user(
            email='otheruser@example.com',
            password='otherpass123'
        )
        admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        recipe = create_recipe(user=other_user)
        self.client.force_authenticate(user=admin_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags."""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag_indian, tags)
        for tag in payload['tags']:
            exists = tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipes tags."""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with new ingredients."""
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 20,
            'price': Decimal('7.00'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Taco Shells'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a recipe with existing ingredients."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Lentils')
        payload = {
            'title': 'Red Lentil Daal',
            'time_minutes': 30,
            'price': Decimal('3.00'),
            'ingredients': [{'name': 'Lentils'}, {'name': 'Tomatoes'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        for ingredient in payload['ingredients']:
            exists = ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Limes'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Limes')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Limes')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Gin')
        payload = {'ingredients': [{'name': 'Gin'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipes ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name='Limes')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_recipes_by_tags(self):
        """Test returning recipes with specific tags."""
        recipe1 = create_recipe(user=self.user, title='Thai vegetable curry')
        recipe2 = create_recipe(user=self.user, title='Aubergine with tahini')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = create_recipe(user=self.user, title='Fish and chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(
            RECIPES_URL,
            params
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients."""
        recipe1 = create_recipe(user=self.user, title='Posh beans on toast')
        recipe2 = create_recipe(user=self.user, title='Chicken cacciatore')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Feta cheese')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Chicken')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = create_recipe(user=self.user, title='Steak and mushrooms')

        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(
            RECIPES_URL,
            params
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class RecipeImageUploadTests(TestCase):
    """Tests for the recipe image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        # Clean up any uploaded images after tests run.
        # This ensures that the test environment remains clean and prevents
        # leftover files from affecting subsequent tests.
        if self.recipe.image:
            self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

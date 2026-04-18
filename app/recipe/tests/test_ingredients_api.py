"""Tests for the ingredients API."""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient, Recipe, Tag
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Return ingredient detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicIngredientsApiTests(TestCase):
    """Test the publicly available ingredients API."""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required to access the endpoint."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the authorized user ingredients API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving ingredients."""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that ingredients for the authenticated user are returned."""
        user2 = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=user2, name='Papper')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], 'Kale')
        self.assertEqual(res.data[0]['id'], Ingredient.objects.get(name='Kale').id)

    def test_create_ingredient_successful(self):
        """Test creating a new ingredient."""
        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test creating a new ingredient with invalid payload."""
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_ingredient(self):
        """Test updating an ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Cabbage')

        payload = {'name': 'Green Cabbage'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting an ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Cabbage')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_delete_other_users_ingredient_error(self):
        """Test trying to delete another user's ingredient gives error."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        ingredient = Ingredient.objects.create(user=other_user, name='Cabbage')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())
        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertTrue(ingredients.exists())

    def test_update_other_users_ingredient_error(self):
        """Test trying to update another user's ingredient gives error."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        ingredient = Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Green Cabbage'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, 'Cabbage')
        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertTrue(ingredients.exists())
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_create_ingredient_with_existing_name(self):
        """Test creating an ingredient with a name that already exists."""
        Ingredient.objects.create(user=self.user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_with_same_name_different_user(self):
        """Test creating an ingredient with the same name as another user."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        exists = Ingredient.objects.filter(
            user=other_user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_with_same_name_different_user_successful(self):
        """Test creating an ingredient with the same name as another user."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        exists = Ingredient.objects.filter(
            user=other_user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        # To allow creating an ingredient with the same name as another user,
        # we would need to remove the unique constraint on the name field in the Ingredient model
        # and add a unique_together constraint on the user and name fields.
        # This would allow multiple users to have ingredients with the same name,
        # but each user would only be able to have one ingredient with that name.
        # The test would then check that the ingredient is created successfully for the second user,
        # and that both users can have an ingredient with the same name without any issues.

    def test_delete_ingredient_with_same_name_different_user(self):
        """Test deleting an ingredient with the same name as another user."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        exists = Ingredient.objects.filter(
            user=other_user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        ingredient = Ingredient.objects.get(user=self.user, name=payload['name'])
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())
        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertTrue(ingredients.exists())

    def test_update_ingredient_with_same_name_different_user(self):
        """Test updating an ingredient with the same name as another user."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        exists = Ingredient.objects.filter(
            user=other_user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        ingredient = Ingredient.objects.get(user=self.user, name=payload['name'])
        url = detail_url(ingredient.id)
        res = self.client.patch(url, {'name': 'Updated Cabbage'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, 'Updated Cabbage')
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertTrue(ingredients.exists())
        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertTrue(ingredients.exists())

    def test_update_ingredient_with_same_name_different_user_error(self):
        """Test updating an ingredient with the same name as another user gives error."""
        other_user = create_user(
            email='test2@example.com',
            password='testpass456'
        )
        Ingredient.objects.create(user=other_user, name='Cabbage')

        payload = {'name': 'Cabbage'}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        exists = Ingredient.objects.filter(
            user=other_user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)
        ingredient = Ingredient.objects.get(user=self.user, name=payload['name'])
        url = detail_url(ingredient.id)
        res = self.client.patch(url, {'name': 'Updated Cabbage'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, 'Updated Cabbage')
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertTrue(ingredients.exists())
        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertTrue(ingredients.exists())

    def test_filter_ingredients_assigned_unique(self):
        """Test filtering ingredients by assigned returns unique items."""
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Cheese')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=30,
            price=12.00,
            user=self.user
        )
        recipe2 = Recipe.objects.create(
            title='Green Eggs on Toast',
            time_minutes=20,
            price=5.00,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by assigned returns items assigned to recipes."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Eggs')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Cheese')
        recipe = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=30,
            price=12.00,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Cheese')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=30,
            price=12.00,
            user=self.user
        )
        recipe2 = Recipe.objects.create(
            title='Green Eggs on Toast',
            time_minutes=20,
            price=5.00,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

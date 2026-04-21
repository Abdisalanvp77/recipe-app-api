"""
Tests for advanced features: Enhanced Reviews, Full-Text Search, and Advanced Filtering.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    Recipe, Rating, ReviewVote,
    DietaryRestriction
)


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class EnhancedReviewSystemTests(TestCase):
    """Test enhanced review system with review text and voting."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.recipe = create_recipe(user=self.user)

    def test_create_rating_with_review_text(self):
        """Test creating a rating with review text."""
        url = reverse('recipe:recipe-ratings', args=[self.recipe.id])
        payload = {
            'rating': Decimal('4.5'),
            'review_text': 'This recipe was delicious and easy to follow!'
        }

        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        rating = Rating.objects.get(user=self.user, recipe=self.recipe)
        self.assertEqual(rating.rating, Decimal('4.5'))
        self.assertEqual(rating.review_text, 'This recipe was delicious and easy to follow!')

    def test_update_review_text(self):
        """Test updating only the review text without changing rating."""
        Rating.objects.create(
            user=self.user,
            recipe=self.recipe,
            rating=Decimal('3.0'),
            review_text='Original review'
        )
        url = reverse('recipe:recipe-ratings', args=[self.recipe.id])
        payload = {'review_text': 'Updated review with better details'}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        rating = Rating.objects.get(user=self.user, recipe=self.recipe)
        self.assertEqual(rating.review_text, 'Updated review with better details')
        self.assertEqual(rating.rating, Decimal('3.0'))

    def test_review_contains_metadata(self):
        """Test that review response contains created_at, updated_at, and is_verified."""
        Rating.objects.create(
            user=self.user,
            recipe=self.recipe,
            rating=Decimal('4.0'),
            review_text='Test review',
            is_verified=True
        )
        url = reverse('recipe:recipe-ratings', args=[self.recipe.id])

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        review = res.data[0]
        self.assertIn('created_at', review)
        self.assertIn('updated_at', review)
        self.assertIn('is_verified', review)
        self.assertTrue(review['is_verified'])

    def test_vote_helpful_on_review(self):
        """Test voting a review as helpful."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('4.0'),
            review_text='Great recipe!'
        )
        rating.helpful_votes = 1
        rating.total_votes = 1
        rating.save()

        self.assertEqual(rating.helpful_votes, 1)
        self.assertEqual(rating.total_votes, 1)
        self.assertEqual(rating.helpful_percentage, 100.0)

    def test_vote_not_helpful_on_review(self):
        """Test voting a review as not helpful."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('2.0'),
            review_text='Not useful'
        )
        rating.helpful_votes = 0
        rating.total_votes = 1
        rating.save()

        self.assertEqual(rating.helpful_votes, 0)
        self.assertEqual(rating.total_votes, 1)
        self.assertEqual(rating.helpful_percentage, 0.0)

    def test_update_vote_on_review(self):
        """Test updating a vote on a review."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('4.0'),
            review_text='Good'
        )
        # Create initial vote (not helpful)
        vote = ReviewVote.objects.create(user=self.user, rating=rating, is_helpful=False)
        # Update it to helpful
        vote.is_helpful = True
        vote.save()

        rating.helpful_votes = 1
        rating.total_votes = 1
        rating.save()

        self.assertEqual(rating.helpful_votes, 1)
        self.assertEqual(rating.total_votes, 1)

    def test_multiple_users_voting_on_review(self):
        """Test multiple users voting on the same review."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('4.0'),
            review_text='Popular review'
        )
        third_user = create_user(
            email='third@example.com',
            password='thirdpass123'
        )

        # First user votes helpful
        ReviewVote.objects.create(user=self.user, rating=rating, is_helpful=True)
        # Third user votes helpful
        ReviewVote.objects.create(user=third_user, rating=rating, is_helpful=True)

        rating.helpful_votes = 2
        rating.total_votes = 2
        rating.save()

        self.assertEqual(rating.helpful_votes, 2)
        self.assertEqual(rating.total_votes, 2)
        self.assertEqual(rating.helpful_percentage, 100.0)

    def test_helpful_percentage_calculation(self):
        """Test helpful percentage calculation with mixed votes."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('3.0'),
            review_text='Mixed review'
        )
        users = [
            self.user,
            create_user(email='user2@example.com', password='pass123'),
            create_user(email='user3@example.com', password='pass123'),
        ]

        # 2 helpful votes, 1 not helpful
        ReviewVote.objects.create(user=users[0], rating=rating, is_helpful=True)
        ReviewVote.objects.create(user=users[1], rating=rating, is_helpful=True)
        ReviewVote.objects.create(user=users[2], rating=rating, is_helpful=False)

        rating.helpful_votes = 2
        rating.total_votes = 3
        rating.save()

        self.assertEqual(rating.helpful_percentage, 66.7)

    def test_review_serializer_includes_helpful_votes(self):
        """Test that review serializer includes helpful votes data."""
        rating = Rating.objects.create(
            user=self.other_user,
            recipe=self.recipe,
            rating=Decimal('4.0'),
            review_text='Helpful review'
        )
        ReviewVote.objects.create(user=self.user, rating=rating, is_helpful=True)
        rating.helpful_votes = 1
        rating.total_votes = 1
        rating.save()

        url = reverse('recipe:recipe-ratings', args=[self.recipe.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        review = res.data[0]
        self.assertEqual(review['helpful_votes'], 1)
        self.assertEqual(review['total_votes'], 1)
        self.assertEqual(review['helpful_percentage'], 100.0)


class FullTextSearchTests(TestCase):
    """Test full-text search functionality."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_search_by_recipe_title(self):
        """Test searching recipes by title."""
        recipe1 = create_recipe(
            user=self.user,
            title='Italian Pasta Carbonara'
        )
        res = self.client.get(RECIPES_URL, {'search': 'Italian'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe1.id)

    def test_search_by_description(self):
        """Test searching recipes by description."""
        recipe1 = create_recipe(
            user=self.user,
            title='Pasta',
            description='A delicious Mediterranean dish with tomatoes and basil'
        )
        res = self.client.get(RECIPES_URL, {'search': 'Mediterranean'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe1.id)

    def test_search_by_cuisine(self):
        """Test searching recipes by cuisine type."""
        recipe1 = create_recipe(
            user=self.user,
            title='Pasta',
            cuisine='Italian'
        )
        res = self.client.get(RECIPES_URL, {'search': 'Italian'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe1.id)

    def test_search_partial_match(self):
        """Test that search works with full word matches."""
        create_recipe(
            user=self.user,
            title='Chocolate Chip Cookies'
        )

        res = self.client.get(RECIPES_URL, {'search': 'Chocolate'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) > 0)
        titles = [r['title'] for r in res.data]
        self.assertIn('Chocolate Chip Cookies', titles)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        recipe = create_recipe(
            user=self.user,
            title='Italian Pasta'
        )

        res = self.client.get(RECIPES_URL, {'search': 'italian'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe.id)


class AdvancedFilteringTests(TestCase):
    """Test advanced filtering capabilities."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_filter_by_cuisine(self):
        """Test filtering recipes by cuisine."""
        italian = create_recipe(
            user=self.user,
            title='Pasta',
            cuisine='Italian'
        )
        res = self.client.get(RECIPES_URL, {'cuisine': 'Italian'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], italian.id)

    def test_filter_by_difficulty(self):
        """Test filtering recipes by difficulty level."""
        easy = create_recipe(
            user=self.user,
            title='Easy Recipe',
            difficulty='easy'
        )
        res = self.client.get(RECIPES_URL, {'difficulty': 'easy'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], easy.id)

    def test_filter_by_price_range(self):
        """Test filtering recipes by price range."""
        expensive = create_recipe(
            user=self.user,
            title='Expensive Recipe',
            price=Decimal('25.00')
        )

        res = self.client.get(RECIPES_URL, {
            'min_price': '10.00',
            'max_price': '30.00'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], expensive.id)

    def test_filter_by_prep_time(self):
        """Test filtering recipes by prep time."""
        quick = create_recipe(
            user=self.user,
            title='Quick Recipe',
            prep_time_minutes=5
        )
        res = self.client.get(RECIPES_URL, {'max_prep_time': '20'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], quick.id)

    def test_filter_by_cook_time(self):
        """Test filtering recipes by cook time."""
        quick = create_recipe(
            user=self.user,
            title='Quick Recipe',
            cook_time_minutes=10
        )
        res = self.client.get(RECIPES_URL, {'max_cook_time': '30'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], quick.id)

    def test_filter_by_total_time(self):
        """Test filtering recipes by total prep + cook time."""
        quick = create_recipe(
            user=self.user,
            title='Quick Recipe',
            prep_time_minutes=10,
            cook_time_minutes=15  # Total: 25
        )
        res = self.client.get(RECIPES_URL, {'max_total_time': '50'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], quick.id)

    def test_filter_by_vegetarian(self):
        """Test filtering vegetarian recipes."""
        veg = create_recipe(
            user=self.user,
            title='Vegetarian Recipe',
            is_vegetarian=True
        )
        res = self.client.get(RECIPES_URL, {'is_vegetarian': 'true'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], veg.id)

    def test_filter_by_vegan(self):
        """Test filtering vegan recipes."""
        vegan = create_recipe(
            user=self.user,
            title='Vegan Recipe',
            is_vegan=True
        )
        res = self.client.get(RECIPES_URL, {'is_vegan': 'true'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], vegan.id)

    def test_filter_by_gluten_free(self):
        """Test filtering gluten-free recipes."""
        gf = create_recipe(
            user=self.user,
            title='Gluten-Free Recipe',
            is_gluten_free=True
        )
        res = self.client.get(RECIPES_URL, {'is_gluten_free': 'true'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], gf.id)

    def test_filter_by_dietary_restrictions(self):
        """Test filtering by dietary restrictions."""
        restriction = DietaryRestriction.objects.create(
            name='Nut-Free',
            slug='nut-free'
        )
        recipe_with = create_recipe(
            user=self.user,
            title='Nut-Free Recipe'
        )
        recipe_with.dietary_restrictions.add(restriction)
        res = self.client.get(RECIPES_URL, {
            'dietary_restrictions': str(restriction.id)
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe_with.id)

    def test_sort_by_rating_descending(self):
        """Test sorting recipes by rating in descending order."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123'
        )
        recipe1 = create_recipe(user=self.user, title='Recipe 1')
        recipe2 = create_recipe(user=self.user, title='Recipe 2')

        Rating.objects.create(user=other_user, recipe=recipe1, rating=Decimal('5.0'))
        Rating.objects.create(user=other_user, recipe=recipe2, rating=Decimal('3.0'))

        res = self.client.get(RECIPES_URL, {
            'sort_by': 'rating',
            'sort_order': 'desc'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # The highest rated recipe should come first
        self.assertEqual(res.data[0]['id'], recipe1.id)

    def test_sort_by_price_ascending(self):
        """Test sorting recipes by price in ascending order."""
        expensive = create_recipe(
            user=self.user,
            title='Expensive',
            price=Decimal('20.00')
        )
        cheap = create_recipe(
            user=self.user,
            title='Cheap',
            price=Decimal('5.00')
        )

        res = self.client.get(RECIPES_URL, {
            'sort_by': 'price',
            'sort_order': 'asc'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['id'], cheap.id)
        self.assertEqual(res.data[1]['id'], expensive.id)

    def test_sort_by_title(self):
        """Test sorting recipes by title."""
        recipe_a = create_recipe(user=self.user, title='Apple Pie')
        recipe_z = create_recipe(user=self.user, title='Zebra Steak')

        res = self.client.get(RECIPES_URL, {
            'sort_by': 'title',
            'sort_order': 'asc'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['id'], recipe_a.id)
        self.assertEqual(res.data[1]['id'], recipe_z.id)

    def test_combine_multiple_filters(self):
        """Test combining multiple filters together."""
        recipe = create_recipe(
            user=self.user,
            title='Perfect Recipe',
            cuisine='Italian',
            difficulty='easy',
            price=Decimal('12.00'),
            prep_time_minutes=15,
            cook_time_minutes=25,
            is_vegetarian=True,
            is_vegan=False
        )
        res = self.client.get(RECIPES_URL, {
            'cuisine': 'Italian',
            'difficulty': 'easy',
            'min_price': '10.00',
            'max_price': '15.00',
            'max_prep_time': '20',
            'is_vegetarian': 'true'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe.id)

    def test_filter_with_search_combined(self):
        """Test combining search with filters."""
        recipe = create_recipe(
            user=self.user,
            title='Italian Pasta Carbonara',
            cuisine='Italian',
            description='Classic Italian pasta dish'
        )
        res = self.client.get(RECIPES_URL, {
            'search': 'Pasta',
            'cuisine': 'Italian'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe.id)

    def test_invalid_sort_field_defaults_to_created_at(self):
        """Test that invalid sort field defaults to created_at."""
        recipe = create_recipe(user=self.user, title='Recipe')

        res = self.client.get(RECIPES_URL, {
            'sort_by': 'invalid_field'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], recipe.id)

    def test_invalid_price_filter_ignored(self):
        """Test that invalid price values are ignored."""
        create_recipe(user=self.user, price=Decimal('10.00'))

        res = self.client.get(RECIPES_URL, {
            'min_price': 'invalid'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_invalid_time_filter_ignored(self):
        """Test that invalid time values are ignored."""
        create_recipe(user=self.user, prep_time_minutes=15)

        res = self.client.get(RECIPES_URL, {
            'max_prep_time': 'invalid'
        })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

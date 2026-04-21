"""URLs for the recipe APIs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from recipe import views

router = DefaultRouter()
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)
router.register('dietary-restrictions', views.DietaryRestrictionViewSet)
router.register('global-tags', views.GlobalTagViewSet)
router.register('global-ingredients', views.GlobalIngredientViewSet)
router.register('collections', views.RecipeCollectionViewSet)

app_name = 'recipe'
urlpatterns = [
    path('', include(router.urls)),
    path('ratings/<int:recipe_id>/', views.RatingViewSet.as_view({
        'get': 'list',
        'post': 'create',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='recipe-ratings'),
    path('ratings/<int:recipe_id>/<int:pk>/vote/', views.RatingViewSet.as_view({
        'post': 'vote_helpful'
    }), name='recipe-rating-vote'),
    path('collections/<int:pk>/remove_recipe/<int:recipe_id>/',
         views.RecipeCollectionViewSet.as_view({'delete': 'remove_recipe'}),
         name='collection-remove-recipe'),
]

"""URLs for the recipe APIs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from recipe import views

router = DefaultRouter()
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)

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
]

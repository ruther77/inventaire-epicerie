<?php

declare(strict_types=1);

use App\Http\Controllers\CartController;
use App\Http\Controllers\CatalogController;
use App\Http\Controllers\ContactController;
use App\Http\Controllers\HomeController;
use App\Http\Controllers\LocaleController;
use App\Http\Livewire\ProductFilter;

$router->get('/', [HomeController::class, '__invoke']);
$router->get('/catalog', [CatalogController::class, 'index']);
$router->get('/catalog/{slug}', [CatalogController::class, 'show']);
$router->get('/cart', [CartController::class, 'index']);
$router->post('/cart', [CartController::class, 'store']);
$router->post('/cart/clear', [CartController::class, 'destroy']);
$router->get('/contact', [ContactController::class, 'create']);
$router->post('/contact', [ContactController::class, 'store']);
$router->get('/locale/{locale}', [LocaleController::class, 'switch']);
$router->post('/livewire/products/filter', [ProductFilter::class, '__invoke']);

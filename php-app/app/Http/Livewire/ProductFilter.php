<?php

declare(strict_types=1);

namespace App\Http\Livewire;

use App\Models\ProductRepository;
use Framework\Http\Response;

final class ProductFilter
{
    public function __construct(private readonly ProductRepository $products = new ProductRepository())
    {
    }

    public function __invoke(): Response
    {
        $request = app()->request();
        $category = $request->input('category');
        $search = $request->input('search');
        if (!app()->session()->validateCsrf($request->input('_token'))) {
            return Response::json(['error' => 'CSRF token mismatch'], 419);
        }

        $products = $this->products->filter($category, $search);
        $html = view('components.product-grid', ['products' => $products]);

        return Response::json([
            'html' => $html,
            'count' => count($products),
        ]);
    }
}

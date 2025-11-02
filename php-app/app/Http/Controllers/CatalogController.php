<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\ProductRepository;
use Framework\Http\Response;

final class CatalogController extends Controller
{
    public function __construct(private readonly ProductRepository $products = new ProductRepository())
    {
        parent::__construct();
    }

    public function index(): Response
    {
        $query = $this->request()->query;

        return $this->view('pages.catalog', [
            'products' => $this->products->filter($query['category'] ?? null, $query['search'] ?? null),
            'categories' => $this->products->categories(),
            'selectedCategory' => $query['category'] ?? null,
            'searchTerm' => $query['search'] ?? null,
        ]);
    }

    public function show(string $slug): Response
    {
        $product = $this->products->findBySlug($slug);

        if ($product === null) {
            return response(view('errors/404'), 404);
        }

        return $this->view('pages.product', [
            'product' => $product,
        ]);
    }
}

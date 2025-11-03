<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\ProductRepository;

final class HomeController extends Controller
{
    public function __construct(private readonly ProductRepository $products = new ProductRepository())
    {
        parent::__construct();
    }

    public function __invoke(): \Framework\Http\Response
    {
        return $this->view('pages.home', [
            'featured' => $this->products->featured(),
            'categories' => $this->products->categories(),
        ]);
    }
}

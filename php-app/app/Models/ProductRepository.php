<?php

declare(strict_types=1);

namespace App\Models;

final class ProductRepository
{
    /**
     * @return array<int, array<string, mixed>>
     */
    public function all(): array
    {
        /** @var array<int, array<string, mixed>> $products */
        $products = require resource_path('data/products.php');

        return $products;
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    public function featured(): array
    {
        return array_slice($this->all(), 0, 3);
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    public function categories(): array
    {
        $categories = [];
        foreach ($this->all() as $product) {
            $categories[$product['category']] = true;
        }

        return array_keys($categories);
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    public function filter(?string $category = null, ?string $search = null): array
    {
        $products = $this->all();

        return array_values(array_filter($products, static function (array $product) use ($category, $search): bool {
            $matchCategory = $category ? strcasecmp($product['category'], $category) === 0 : true;
            $matchSearch = $search ? str_contains(mb_strtolower($product['name']), mb_strtolower($search)) : true;

            return $matchCategory && $matchSearch;
        }));
    }

    public function findBySlug(string $slug): ?array
    {
        foreach ($this->all() as $product) {
            if ($product['slug'] === $slug) {
                return $product;
            }
        }

        return null;
    }
}

<?php

declare(strict_types=1);

namespace App\Support;

final class Cart
{
    private const SESSION_KEY = 'cart.items';

    /**
     * @param array<string, mixed> $product
     */
    public function add(array $product, int $quantity = 1): void
    {
        $items = $this->items();
        $key = (string) $product['id'];
        if (!isset($items[$key])) {
            $items[$key] = [
                'product' => $product,
                'quantity' => 0,
            ];
        }

        $items[$key]['quantity'] += $quantity;
        $_SESSION[self::SESSION_KEY] = $items;
    }

    /**
     * @return array<string, array{product:array<string,mixed>,quantity:int}>
     */
    public function items(): array
    {
        return $_SESSION[self::SESSION_KEY] ?? [];
    }

    public function total(): float
    {
        return array_reduce($this->items(), static function (float $carry, array $item): float {
            return $carry + ($item['product']['price'] * $item['quantity']);
        }, 0.0);
    }

    public function clear(): void
    {
        unset($_SESSION[self::SESSION_KEY]);
    }
}
